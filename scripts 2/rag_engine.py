import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_DIR = PROJECT_ROOT / "vector_db" / "chroma"
COLLECTION_NAME = "vehicle_specs"

TOP_K_VECTOR = 8
TOP_K_KEYWORD = 12
TOP_K_FINAL = 6
RRF_K = 60

_TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "what", "which", "is", "are", "the", "a", "an", "of", "to", "for", "in", "on", "and", "or",
    "does", "do", "did", "have", "has", "with", "without", "please", "tell", "me", "about",
    "explain", "simple", "words", "cambodia"
}

INTENT_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("warranty", re.compile(r"\b(warranty|guarantee|coverage|covered)\b", re.I)),
    ("colors", re.compile(r"\b(color|colour|colors|colours|paint)\b", re.I)),
    ("wireless_charging", re.compile(r"\b(wireless\s+charging|wireless\s+charger|qi|charging\s+pad)\b", re.I)),
    ("ambient_lighting", re.compile(r"\b(ambient\s+lighting|ambient\s+light|mood\s+lighting)\b", re.I)),
    ("service", re.compile(r"\b(service\s+interval|maintenance|free\s+service|service\s+package)\b", re.I)),
]

INTENT_KEYWORDS: Dict[str, List[str]] = {
    "warranty": ["warranty", "guarantee", "coverage", "covered", "warranty period", "warranty coverage", "years", "year", "km"],
    "colors": ["color", "colour", "colors", "colours", "paint", "exterior color"],
    "wireless_charging": ["wireless charging", "wireless charger", "qi", "charging pad"],
    "ambient_lighting": ["ambient lighting", "ambient light", "mood lighting"],
    "service": ["service interval", "maintenance", "free service", "service package"],
}


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


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


def detect_intent(question: str) -> Optional[str]:
    q = question or ""
    for name, pat in INTENT_PATTERNS:
        if pat.search(q):
            return name
    return None


def build_query_keywords(question: str) -> List[str]:
    q = normalize_ws(question)
    toks = [t for t in tokenize(q) if t and t not in STOPWORDS]
    out: List[str] = []
    for t in toks:
        if t not in out:
            out.append(t)

    if "wireless" in out or "charger" in out or "charging" in out:
        for x in ["wireless charging", "wireless charger", "qi", "charging pad"]:
            if x not in out:
                out.append(x)

    if "color" in out or "colors" in out or "colour" in out or "colours" in out or "paint" in out:
        for x in ["color", "colors", "paint", "exterior color"]:
            if x not in out:
                out.append(x)

    if "warranty" in out or "coverage" in out or "guarantee" in out:
        for x in ["warranty", "coverage", "guarantee", "warranty period", "years", "km"]:
            if x not in out:
                out.append(x)

    return out


def extract_evidence_lines(docs: List[str], keywords: List[str], max_lines: int = 6) -> List[str]:
    def is_noise(line: str) -> bool:
        low = line.strip().lower()
        if not low:
            return True
        if low.startswith("source:"):
            return True
        if low.startswith("http://") or low.startswith("https://"):
            return True
        return False

    keys = [k.strip().lower() for k in (keywords or []) if k and k.strip()]
    if not keys:
        return []

    scored: Dict[str, int] = {}

    for d in docs:
        for line in d.splitlines():
            clean = line.strip()
            if is_noise(clean):
                continue
            low = clean.lower()

            hit = 0
            for k in keys:
                if k in low:
                    hit += 1

            if hit > 0:
                if clean not in scored or hit > scored[clean]:
                    scored[clean] = hit

    ranked = sorted(scored.items(), key=lambda x: (-x[1], len(x[0])))
    return [x[0] for x in ranked[:max_lines]]


def find_model_global(full_rows: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    t_norm = normalize_ws(text)
    t_comp = compact(text)
    hits = []
    for r in full_rows:
        model = r.get("model") or ""
        if normalize_ws(model) and normalize_ws(model) in t_norm:
            hits.append(r)
        elif compact(model) and compact(model) in t_comp:
            hits.append(r)
    return hits


def best_model_guess(full_rows: List[Dict[str, Any]], text: str) -> Optional[Dict[str, Any]]:
    t = normalize_ws(text)
    t_tokens = set(t.split())
    best = None
    best_score = 0

    for r in full_rows:
        model = normalize_ws(r.get("model") or "")
        if not model:
            continue
        tokens = set(model.split())
        score = len(tokens.intersection(t_tokens))
        if score > best_score:
            best_score = score
            best = r

    return best if best_score >= 2 else None


class RAGEngine:
    def __init__(self, full_rows: List[Dict[str, Any]]):
        self.full_rows = full_rows
        self.collection = connect_chroma()

    def resolve_target(self, question: str, last_model_norm: Optional[str]) -> Optional[Dict[str, Any]]:
        if last_model_norm:
            for r in self.full_rows:
                if normalize_ws(r.get("model") or "") == normalize_ws(last_model_norm):
                    return r

        hits = find_model_global(self.full_rows, question)
        if hits:
            return hits[0]

        return best_model_guess(self.full_rows, question)

    def rag_answer(self, question: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
        target = self.resolve_target(question, last_model_norm)
        if not target:
            return {
                "answer_type": "rag",
                "text": "Please specify which model you mean (example: 'spec of Corolla Cross HEV').",
                "facts": [],
                "sources": [],
            }

        docs, metas = hybrid_retrieve(self.collection, question, target, TOP_K_FINAL)

        urls: List[str] = []
        for m in metas:
            u = (m or {}).get("url")
            if u and u not in urls:
                urls.append(u)

        intent = detect_intent(question)
        if intent and intent in INTENT_KEYWORDS:
            keywords = INTENT_KEYWORDS[intent]
        else:
            keywords = build_query_keywords(question)

        evidence = extract_evidence_lines(docs, keywords=keywords, max_lines=6)

        model_name = f"{target.get('brand','').strip()} {target.get('model','').strip()}".strip()

        gated_intents = {"warranty", "colors", "wireless_charging", "ambient_lighting", "service"}
        if intent in gated_intents and not evidence:
            text = f"I couldn't find {intent.replace('_', ' ')} information in the official text we captured for {model_name}."
            return {"answer_type": "rag", "text": text, "facts": [], "sources": urls}

        if evidence:
            text = (
                f"I found relevant official text for {model_name}. Here are the most relevant snippets:\n"
                + "\n".join(f"- {e}" for e in evidence)
            )
        else:
            text = f"I found related official text for {model_name}, but no strong matching lines were extracted."

        return {
            "answer_type": "rag",
            "text": text,
            "facts": evidence,
            "sources": urls,
        }