import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

# ==========================================================
# CONFIG
# ==========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_MIN = PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv"
DB_DIR = PROJECT_ROOT / "vector_db" / "chroma"
COLLECTION_NAME = "vehicle_specs"

FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}
SEATS_FALLBACK_FIELDS = ("seats", "spec_seating_capacity")

TOP_K_VECTOR = 8
TOP_K_KEYWORD = 12
TOP_K_FINAL = 6
RRF_K = 60


# ==========================================================
# CSV LOAD
# ==========================================================
def load_min_table() -> List[Dict[str, Any]]:
    with CSV_MIN.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return int(float(s.replace(",", "")))
    except Exception:
        return None


def get_seats_value(row: Dict[str, Any]) -> Optional[int]:
    for key in SEATS_FALLBACK_FIELDS:
        if key in row:
            v = to_int(row.get(key))
            if v is not None:
                return v
    return None


def fmt_na(v: Any) -> str:
    s = str(v).strip() if v is not None else ""
    return "N/A" if not s else s


def fmt_na_int(v: Optional[int]) -> str:
    return "N/A" if v is None else str(v)


# ==========================================================
# NLU
# ==========================================================
def extract_budget(text: str) -> Optional[int]:
    m = re.search(r"\$?\s*([\d,]{4,})", text, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def extract_seats(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(seat|seats|seater)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def extract_fuel(text: str) -> Optional[str]:
    t = text.lower()
    t = (
        t.replace("disel", "diesel")
        .replace("gazoline", "gasoline")
        .replace("gasolin", "gasoline")
        .replace("petrol", "gasoline")
        .replace("hybird", "hybrid")
    )
    for f in FUELS:
        if re.search(rf"\b{re.escape(f)}\b", t):
            return f
    return None


def looks_like_question(text: str) -> bool:
    t = text.lower().strip()
    if "?" in t:
        return True

    starters = (
        "does ", "do ", "is ", "are ",
        "what ", "which ", "tell me", "can you", "have ",
        "spec of", "specs of", "specification", "details of", "feature of", "features of",
    )
    return t.startswith(starters)


def looks_like_spec_request(text: str) -> bool:
    t = text.lower().strip()
    return bool(re.search(r"\b(spec|specs|specification|details|full spec)\b", t))


def parse_constraints(text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    return extract_budget(text), extract_seats(text), extract_fuel(text)


# ==========================================================
# SLOT FILLING
# ==========================================================
def ask_missing(slots: Dict[str, Any]) -> Optional[str]:
    q = []
    if slots["max_budget"] is None:
        q.append("What is your maximum budget (USD)?")
    if slots["min_seats"] is None:
        q.append("How many seats do you strictly need?")
    if slots["fuel"] is None:
        q.append("Fuel preference: Diesel / Gasoline / Hybrid / EV / Any")
    return None if not q else "To give you a precise recommendation, please tell me:\n- " + "\n- ".join(q)


# ==========================================================
# STRUCTURED FILTER
# ==========================================================
def filter_cars(rows, max_budget, min_seats, fuel):
    res = []
    for r in rows:
        price = to_int(r.get("price_usd"))
        seats = get_seats_value(r)
        row_fuel = (r.get("fuel") or "").lower().strip()

        if price is None:
            continue
        if price > max_budget:
            continue

        if seats is not None and seats < min_seats:
            continue

        if fuel != "any" and row_fuel != fuel:
            continue

        res.append(r)

    return sorted(res, key=lambda x: to_int(x.get("price_usd")) or 0, reverse=True)


# ==========================================================
# MODEL RESOLUTION (BETTER: handles "hiluxvigo")
# ==========================================================
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def pick_target_model(text: str, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    t_norm = normalize_ws(text)
    t_comp = compact(text)

    for c in candidates:
        model = c.get("model") or ""
        if normalize_ws(model) and normalize_ws(model) in t_norm:
            return c
        if compact(model) and compact(model) in t_comp:
            return c

    return None


def find_model_global(rows: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    t_norm = normalize_ws(text)
    t_comp = compact(text)
    hits = []
    for r in rows:
        model = r.get("model") or ""
        if normalize_ws(model) and normalize_ws(model) in t_norm:
            hits.append(r)
        elif compact(model) and compact(model) in t_comp:
            hits.append(r)
    return hits


def best_model_guess(rows: List[Dict[str, Any]], text: str) -> Optional[Dict[str, Any]]:
    t = normalize_ws(text)
    t_tokens = set(t.split())
    best = None
    best_score = 0

    for r in rows:
        model = normalize_ws(r.get("model") or "")
        if not model:
            continue
        tokens = set(model.split())
        score = len(tokens.intersection(t_tokens))
        if score > best_score:
            best_score = score
            best = r

    return best if best_score >= 2 else None


# ==========================================================
# CHROMA (VECTOR)
# ==========================================================
def connect_chroma():
    client = chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(COLLECTION_NAME)


def chroma_where_brand_model(brand: str, model: str) -> Dict[str, Any]:
    return {"$and": [{"brand": brand}, {"model": model}]}


def vector_retrieve(collection, query: str, target: Dict[str, Any], top_k: int) -> List[Dict[str, Any]]:
    res = collection.query(
        query_texts=[query],
        where=chroma_where_brand_model(target["brand"], target["model"]),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = res["documents"][0] if res.get("documents") else []
    metas = res["metadatas"][0] if res.get("metadatas") else []
    dists = res["distances"][0] if res.get("distances") else []

    out = []
    for i in range(min(len(docs), len(metas))):
        out.append({"doc": docs[i], "meta": metas[i], "distance": dists[i] if i < len(dists) else None})
    return out


def get_all_docs_for_model(collection, target: Dict[str, Any]) -> List[Dict[str, Any]]:
    got = collection.get(
        where=chroma_where_brand_model(target["brand"], target["model"]),
        include=["documents", "metadatas"],
    )
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    return [{"doc": docs[i], "meta": metas[i]} for i in range(min(len(docs), len(metas)))]


# ==========================================================
# BM25 (KEYWORD)
# ==========================================================
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, docs: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs = docs
        self.tokens = [tokenize(d) for d in docs]
        self.doc_len = [len(t) for t in self.tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0

        self.df = Counter()
        self.tf = []
        for tks in self.tokens:
            c = Counter(tks)
            self.tf.append(c)
            for term in c.keys():
                self.df[term] += 1

        self.N = len(self.docs)

    def idf(self, term: str) -> float:
        n_q = self.df.get(term, 0)
        return math.log(1 + (self.N - n_q + 0.5) / (n_q + 0.5)) if self.N > 0 else 0.0

    def score(self, query: str) -> List[float]:
        q_terms = tokenize(query)
        scores = [0.0] * self.N

        for i in range(self.N):
            dl = self.doc_len[i] if self.doc_len else 0
            denom_norm = self.k1 * (1 - self.b + self.b * (dl / self.avgdl)) if self.avgdl > 0 else self.k1

            for term in q_terms:
                freq = self.tf[i].get(term, 0)
                if freq == 0:
                    continue
                idf = self.idf(term)
                scores[i] += idf * ((freq * (self.k1 + 1)) / (freq + denom_norm))

        return scores


def keyword_retrieve(docs_with_meta: List[Dict[str, Any]], query: str, top_k: int) -> List[Dict[str, Any]]:
    docs = [d["doc"] for d in docs_with_meta]
    bm25 = BM25Index(docs)
    scores = bm25.score(query)

    idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [{"doc": docs_with_meta[i]["doc"], "meta": docs_with_meta[i]["meta"], "bm25": scores[i]} for i in idxs]


def rrf_fuse(vec_items: List[Dict[str, Any]], kw_items: List[Dict[str, Any]], top_k: int, k: int = 60) -> List[Dict[str, Any]]:
    def key_of(item: Dict[str, Any]) -> str:
        meta = item.get("meta") or {}
        url = str(meta.get("url") or "") if isinstance(meta, dict) else ""
        return f"{item.get('doc','')}||{url}"

    score_map = defaultdict(float)
    item_map = {}

    for rank, it in enumerate(vec_items, start=1):
        key = key_of(it)
        score_map[key] += 1.0 / (k + rank)
        item_map[key] = it

    for rank, it in enumerate(kw_items, start=1):
        key = key_of(it)
        score_map[key] += 1.0 / (k + rank)
        if key not in item_map:
            item_map[key] = it

    fused = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [item_map[kv[0]] for kv in fused]


def hybrid_retrieve(collection, query: str, target: Dict[str, Any], top_k_final: int) -> Tuple[List[str], List[Dict[str, Any]]]:
    vec = vector_retrieve(collection, query, target, TOP_K_VECTOR)
    all_docs = get_all_docs_for_model(collection, target)
    kw = keyword_retrieve(all_docs, query, TOP_K_KEYWORD)

    fused = rrf_fuse(vec, kw, top_k_final, k=RRF_K)
    docs = [x["doc"] for x in fused]
    metas = [x.get("meta") or {} for x in fused]
    return docs, metas


# ==========================================================
# FEATURE QA: DETERMINISTIC FROM CSV (NO HALLUCINATION)
# ==========================================================
FEATURE_ALIASES = {
    "360 camera": ["spec_panoramic_view_monitor_pvm", "spec_panoramic_view_monitor", "spec_pvm"],
    "panoramic view monitor": ["spec_panoramic_view_monitor_pvm"],
    "pvm": ["spec_panoramic_view_monitor_pvm"],
    "reverse camera": ["spec_reverse_camera"],
    "back camera": ["spec_reverse_camera"],
    "carplay": ["spec_apple_carplay_and_android_auto", "spec_apple_carplay_or_android_auto"],
    "android auto": ["spec_apple_carplay_and_android_auto", "spec_apple_carplay_or_android_auto"],
    "turning radius": ["spec_minimum_turning_radius_tire"],
    "safety rating": ["spec_safety_rating"],
}


def detect_feature_key(question: str) -> Optional[str]:
    t = question.lower()
    for phrase in FEATURE_ALIASES.keys():
        if phrase in t:
            return phrase
    # also allow "360" alone
    if re.search(r"\b360\b", t) and ("camera" in t or "view" in t):
        return "360 camera"
    return None


def answer_feature_from_csv(target: Dict[str, Any], feature_phrase: str) -> Optional[str]:
    keys = FEATURE_ALIASES.get(feature_phrase, [])
    for k in keys:
        if k in target:
            v = fmt_na(target.get(k))
            if v != "N/A":
                # IMPORTANT: show the exact field used -> audit-friendly
                return f"{feature_phrase}: {v}  (field: {k})"
    return None


# ==========================================================
# ANSWERING
# ==========================================================
def spec_summary_from_csv(target: Dict[str, Any]) -> str:
    seats_val = get_seats_value(target)
    return "\n".join(
        [
            f"{target.get('brand','')} {target.get('model','')} official specifications (from CSV):",
            f"- Price (USD): {fmt_na(target.get('price_usd'))}",
            f"- Seats: {fmt_na_int(seats_val)}",
            f"- Fuel: {fmt_na(target.get('fuel'))}",
            f"- Body Type: {fmt_na(target.get('body_type'))}",
            "",
            f"Source: {fmt_na(target.get('url'))}",
        ]
    )


def extract_evidence_lines(docs: List[str], keywords: List[str], max_lines: int = 3) -> List[str]:
    lines_out = []
    for d in docs:
        for line in d.splitlines():
            low = line.lower()
            if any(k in low for k in keywords):
                clean = line.strip()
                if clean and clean not in lines_out:
                    lines_out.append(clean)
            if len(lines_out) >= max_lines:
                return lines_out
    return lines_out


# ==========================================================
# MAIN
# ==========================================================
def main():
    rows = load_min_table()
    collection = connect_chroma()

    slots = {"max_budget": None, "min_seats": None, "fuel": None}
    candidates: List[Dict[str, Any]] = []
    last_target: Optional[Dict[str, Any]] = None  # conversation memory

    print("Car Chatbot (Structured Filter + Hybrid RAG Q&A)")
    print("Type 'exit' to quit. Type 'new' to restart.\n")

    while True:
        user = input("You: ").strip()
        if not user:
            continue

        if user.lower() in {"exit", "quit"}:
            break

        if user.lower() in {"new", "restart"}:
            slots = {"max_budget": None, "min_seats": None, "fuel": None}
            candidates = []
            last_target = None
            print("\nBot: OK. Tell me your budget, seats, and fuel.\n")
            continue

        # ---------------- Q&A MODE ----------------
        if looks_like_question(user) or looks_like_spec_request(user):
            global_matches = find_model_global(rows, user)
            target = pick_target_model(user, candidates) or (global_matches[0] if global_matches else None)

            if not target:
                target = best_model_guess(rows, user)

            # If still no model mentioned, use last_target (real chatbot behavior)
            if not target and last_target:
                target = last_target

            if not target:
                print("\nBot: Please specify which model you mean (example: 'spec of Corolla Cross HEV').\n")
                continue

            last_target = target  # update memory

            # Spec request -> CSV summary
            if looks_like_spec_request(user) and ("?" not in user):
                print("\nBot: " + spec_summary_from_csv(target) + "\n")
                continue

            # Feature QA (deterministic from CSV first)
            feature_phrase = detect_feature_key(user)
            if feature_phrase:
                ans = answer_feature_from_csv(target, feature_phrase)
                if ans:
                    print("\nBot: From official specs (CSV):")
                    print(f"- {ans}")
                    print(f"Source: {fmt_na(target.get('url'))}\n")
                    print("Note: If this is wrong in real life, it means the CSV field mapping/scraping needs correction.\n")
                    continue

            # Otherwise fallback to hybrid retrieval
            docs, metas = hybrid_retrieve(collection, user, target, TOP_K_FINAL)

            # evidence snippets (helps transparency)
            evidence = extract_evidence_lines(docs, keywords=["camera", "pvm", "panoramic", "reverse", "carplay", "turning", "radius", "safety"])
            if evidence:
                print("\nBot: Retrieved evidence (snippets):")
                for e in evidence:
                    print(f"- {e}")

            # generic fallback message
            print("\nBot: I found related official text, but I couldn't map an exact spec field for your question.")
            url = target.get("url")
            print(f"Source: {fmt_na(url)}\n")
            continue

        # ---------------- RECOMMENDATION MODE ----------------
        b, s, f = parse_constraints(user)

        if b is not None:
            slots["max_budget"] = b
        if s is not None:
            slots["min_seats"] = s
        if f is not None:
            slots["fuel"] = f

        missing = ask_missing(slots)
        if missing:
            print(f"\nBot: {missing}\n")
            continue

        candidates = filter_cars(rows, slots["max_budget"], slots["min_seats"], slots["fuel"])
        slots = {"max_budget": None, "min_seats": None, "fuel": None}

        if not candidates:
            print("\nBot: I couldn't find an official match. Try adjusting your constraints.\n")
            continue

        verified = []
        possible = []
        for c in candidates:
            seats_val = get_seats_value(c)
            if seats_val is None:
                possible.append(c)
            else:
                verified.append(c)

        if verified:
            print("\nBot: Based on your requirements, here are official matches:\n")
            for c in verified:
                seats_val = get_seats_value(c)
                print(f"- {c['brand']} {c['model']} (${c['price_usd']}), seats={fmt_na_int(seats_val)}, fuel={c['fuel']}")
                print(f"  Source: {c['url']}\n")

        if possible:
            print("Bot: Possible matches (some required fields are N/A in CSV):\n")
            for c in possible:
                seats_val = get_seats_value(c)
                print(f"- {c['brand']} {c['model']} (${c['price_usd']}), seats={fmt_na_int(seats_val)}, fuel={c['fuel']}")
                print(f"  Source: {c['url']}\n")

        # Set last_target to top result to enable follow-up questions naturally
        last_target = verified[0] if verified else (possible[0] if possible else None)

        print("Bot: Ask about any model shown. Examples:")
        print("- spec of Corolla Cross HEV")
        print("- Does it have 360 camera?   (uses last shown model)")
        print("- Does Corolla Cross HEV have reverse camera?\n")


if __name__ == "__main__":
    main()