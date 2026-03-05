# import csv
# import re
# from pathlib import Path
# from typing import Dict, Any, List, Optional, Tuple
#
# import chromadb
# from chromadb.config import Settings
#
# # ==========================================================
# # 5.chat_rag.py
# # ==========================================================
# # Purpose:
# #   A simple hybrid chatbot for car services:
# #     1) Recommendation (Structured Retrieval): filter vehicles from CSV by constraints
# #     2) Technical Q&A (Dense Retrieval): search relevant spec chunks in ChromaDB
# #     3) Answering (Extractive QA): extract exact spec lines using regex (no LLM)
# #
# # Key techniques used:
# #   - Rule-based NLU (regex extraction for budget/seats/fuel)
# #   - Slot filling (ask follow-up questions until constraints are complete)
# #   - Intent routing (Recommendation vs Q&A)
# #   - Structured retrieval (CSV boolean filtering)
# #   - Dense retrieval (vector search in ChromaDB)
# #   - Extractive QA (pattern matching to avoid hallucination)
# #   - Evidence output (show official source URL from metadata)
# # ==========================================================
#
# # ==========================================================
# # PROJECT CONFIGURATION
# # ==========================================================
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# CSV_MIN = PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv"
# DB_DIR = PROJECT_ROOT / "vector_db" / "chroma"
# COLLECTION_NAME = "vehicle_specs"
#
# FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}
#
# # If seats column is missing, we can fallback to spec_seating_capacity if present.
# SEATS_FALLBACK_FIELDS = ("seats", "spec_seating_capacity")
#
#
# # ==========================================================
# # LOAD STRUCTURED DATA (CSV)
# # ==========================================================
# def load_min_table() -> List[Dict[str, Any]]:
#     with CSV_MIN.open("r", encoding="utf-8", newline="") as f:
#         return list(csv.DictReader(f))
#
#
# def to_int(v) -> Optional[int]:
#     try:
#         if v is None:
#             return None
#         s = str(v).strip()
#         if not s:
#             return None
#         return int(float(s.replace(",", "")))
#     except Exception:
#         return None
#
#
# def get_seats_value(row: Dict[str, Any]) -> Optional[int]:
#     """
#     Seats resolver:
#       - Try seats
#       - Else try spec_seating_capacity
#       - Else return None (meaning N/A)
#     """
#     for key in SEATS_FALLBACK_FIELDS:
#         if key in row:
#             v = to_int(row.get(key))
#             if v is not None:
#                 return v
#     return None
#
#
# def fmt_na_int(v: Optional[int]) -> str:
#     return "N/A" if v is None else str(v)
#
#
# # ==========================================================
# # SLOT EXTRACTION (RULE-BASED NLU)
# # ==========================================================
# def extract_budget(text: str) -> Optional[int]:
#     m = re.search(r"\$?\s*([\d,]{4,})", text)
#     if not m:
#         return None
#     return int(m.group(1).replace(",", ""))
#
#
# def extract_seats(text: str) -> Optional[int]:
#     m = re.search(r"(\d+)\s*(seat|seats|seater)", text, re.IGNORECASE)
#     return int(m.group(1)) if m else None
#
#
# def extract_fuel(text: str) -> Optional[str]:
#     t = text.lower()
#     t = (
#         t.replace("disel", "diesel")
#          .replace("gazoline", "gasoline")
#          .replace("petrol", "gasoline")
#          .replace("hybird", "hybrid")
#     )
#
#     for f in FUELS:
#         if re.search(rf"\b{f}\b", t):
#             return f
#     return None
#
#
# # ==========================================================
# # INTENT DETECTION (QUERY ROUTING)
# # ==========================================================
# def looks_like_question(text: str) -> bool:
#     t = text.lower().strip()
#     if "?" in t:
#         return True
#
#     starters = (
#         "does ", "do ", "is ", "are ",
#         "what ", "which ", "tell me", "can you", "have "
#     )
#     return t.startswith(starters)
#
#
# def parse_constraints(text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
#     return extract_budget(text), extract_seats(text), extract_fuel(text)
#
#
# # ==========================================================
# # SLOT FILLING (DIALOG MANAGEMENT)
# # ==========================================================
# def ask_missing(slots: Dict[str, Any]) -> Optional[str]:
#     q = []
#     if slots["max_budget"] is None:
#         q.append("What is your maximum budget (USD)?")
#     if slots["min_seats"] is None:
#         q.append("How many seats do you strictly need?")
#     if slots["fuel"] is None:
#         q.append("Fuel preference: Diesel / Gasoline / Hybrid / EV / Any")
#
#     return None if not q else "To give you a precise recommendation, please tell me:\n- " + "\n- ".join(q)
#
#
# # ==========================================================
# # DETERMINISTIC FILTERING (STRUCTURED RETRIEVAL)
# # ==========================================================
# def filter_cars(rows, max_budget, min_seats, fuel):
#     res = []
#     for r in rows:
#         price = to_int(r.get("price_usd"))
#         seats = get_seats_value(r)
#         row_fuel = (r.get("fuel") or "").lower().strip()
#
#         if price is None:
#             continue
#
#         if price > max_budget:
#             continue
#
#         # Seats constraint only enforced when seats is known.
#         # If seats is missing => keep as possible match.
#         if seats is not None and seats < min_seats:
#             continue
#
#         if fuel != "any" and row_fuel != fuel:
#             continue
#
#         res.append(r)
#
#     return sorted(res, key=lambda x: to_int(x.get("price_usd")) or 0, reverse=True)
#
#
# # ==========================================================
# # VECTOR DATABASE (DENSE RETRIEVAL)
# # ==========================================================
# def connect_chroma():
#     client = chromadb.PersistentClient(
#         path=str(DB_DIR),
#         settings=Settings(anonymized_telemetry=False),
#     )
#     return client.get_or_create_collection(COLLECTION_NAME)
#
#
# def retrieve_context(collection, query, target, top_k=4):
#     res = collection.query(
#         query_texts=[query],
#         where={"brand": target["brand"], "model": target["model"]},
#         n_results=top_k,
#         include=["documents", "metadatas"],
#     )
#     return res["documents"][0], res["metadatas"][0]
#
#
# # ==========================================================
# # MODEL RESOLUTION (WHICH CAR IS USER ASKING ABOUT?)
# # ==========================================================
# def pick_target_model(text, candidates):
#     t = text.lower()
#     for c in candidates:
#         model = (c.get("model") or "").lower()
#         if model and model in t:
#             return c
#     return None
#
#
# def find_model_global(rows, text):
#     t = text.lower()
#     return [r for r in rows if (r.get("model") or "").lower() in t]
#
#
# # ==========================================================
# # EXTRACTIVE QUESTION ANSWERING (NO LLM)
# # ==========================================================
# def answer_from_context(question, docs):
#     if not docs:
#         return "I do not have that information in the provided official data."
#
#     ctx = "\n".join(docs)
#
#     patterns = [
#         ("Reverse camera", r"Reverse camera\s*:\s*(.+)"),
#         ("Turning radius", r"Minimum turning radius\s*:\s*(.+)"),
#         ("Fold-up seats", r"Fold-up.*seat.*:\s*(.+)"),
#     ]
#
#     answers = []
#     for label, p in patterns:
#         m = re.search(p, ctx, re.IGNORECASE)
#         if m:
#             answers.append(f"{label}: {m.group(1).strip()}")
#
#     if answers:
#         return "From official specs:\n- " + "\n- ".join(answers)
#
#     return "I found related information, but not an exact specification line."
#
#
# # ==========================================================
# # MAIN CHAT LOOP (STATE MACHINE)
# # ==========================================================
# def main():
#     rows = load_min_table()
#     collection = connect_chroma()
#
#     slots = {"max_budget": None, "min_seats": None, "fuel": None}
#     candidates = []
#
#     print("Car Chatbot (Slot Filling + CSV Filter + RAG Q&A)")
#     print("Type 'exit' to quit. Type 'new' to restart.\n")
#
#     while True:
#         user = input("You: ").strip()
#
#         if user.lower() in {"exit", "quit"}:
#             break
#
#         if user.lower() in {"new", "restart"}:
#             slots = {"max_budget": None, "min_seats": None, "fuel": None}
#             candidates = []
#             print("\nBot: OK, tell me your budget, seats, and fuel.\n")
#             continue
#
#         # ---------------- Q&A MODE ----------------
#         if looks_like_question(user):
#             global_matches = find_model_global(rows, user)
#             target = pick_target_model(user, candidates) or (global_matches[0] if global_matches else None)
#
#             if not target:
#                 print("\nBot: Please specify which model you mean.\n")
#                 continue
#
#             docs, metas = retrieve_context(collection, user, target)
#             print(f"\nBot: {answer_from_context(user, docs)}")
#
#             if metas and metas[0].get("url"):
#                 print(f"Source: {metas[0]['url']}\n")
#             continue
#
#         # ---------------- RECOMMENDATION MODE ----------------
#         b, s, f = parse_constraints(user)
#
#         if b is not None:
#             slots["max_budget"] = b
#         if s is not None:
#             slots["min_seats"] = s
#         if f is not None:
#             slots["fuel"] = f
#
#         missing = ask_missing(slots)
#         if missing:
#             print(f"\nBot: {missing}\n")
#             continue
#
#         candidates = filter_cars(rows, slots["max_budget"], slots["min_seats"], slots["fuel"])
#         slots = {"max_budget": None, "min_seats": None, "fuel": None}
#
#         if not candidates:
#             print("\nBot: I couldn't find an official match. Try adjusting your constraints.\n")
#             continue
#
#         verified = []
#         possible = []
#         for c in candidates:
#             seats_val = get_seats_value(c)
#             if seats_val is None:
#                 possible.append(c)
#             else:
#                 verified.append(c)
#
#         if verified:
#             print("\nBot: Based on your requirements, here are official matches:\n")
#             for c in verified:
#                 seats_val = get_seats_value(c)
#                 print(f"- {c['brand']} {c['model']} (${c['price_usd']}), seats={fmt_na_int(seats_val)}, fuel={c['fuel']}")
#                 print(f"  Source: {c['url']}\n")
#
#         if possible:
#             print("Bot: Possible matches (some required fields are N/A in CSV):\n")
#             for c in possible:
#                 seats_val = get_seats_value(c)
#                 print(f"- {c['brand']} {c['model']} (${c['price_usd']}), seats={fmt_na_int(seats_val)}, fuel={c['fuel']}")
#                 print(f"  Source: {c['url']}\n")
#
#         print("Bot: You can now ask technical questions about these models.\n")
#
# if __name__ == "__main__":
#     main()
# Code below good result
import csv
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

# ==========================================================
# 5.chat_rag.py
# ==========================================================
# Purpose:
#   A simple hybrid chatbot for car services:
#     1) Recommendation (Structured Retrieval): filter vehicles from CSV by constraints
#     2) Technical Q&A (Dense Retrieval): search relevant spec chunks in ChromaDB
#     3) Answering (Extractive QA): extract exact spec lines using regex (no LLM)
#
# Key techniques used:
#   - Rule-based NLU (regex extraction for budget/seats/fuel)
#   - Slot filling (ask follow-up questions until constraints are complete)
#   - Intent routing (Recommendation vs Q&A)
#   - Structured retrieval (CSV boolean filtering)
#   - Dense retrieval (vector search in ChromaDB)
#   - Extractive QA (pattern matching to avoid hallucination)
#   - Evidence output (show official source URL from metadata)
# ==========================================================

# ==========================================================
# PROJECT CONFIGURATION
# ==========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_MIN = PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv"
DB_DIR = PROJECT_ROOT / "vector_db" / "chroma"
COLLECTION_NAME = "vehicle_specs"

FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}

# If seats column is missing, we can fallback to spec_seating_capacity if present.
SEATS_FALLBACK_FIELDS = ("seats", "spec_seating_capacity")


# ==========================================================
# LOAD STRUCTURED DATA (CSV)
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
    """
    Seats resolver:
      - Try seats
      - Else try spec_seating_capacity
      - Else return None (meaning N/A)
    """
    for key in SEATS_FALLBACK_FIELDS:
        if key in row:
            v = to_int(row.get(key))
            if v is not None:
                return v
    return None


def fmt_na_int(v: Optional[int]) -> str:
    return "N/A" if v is None else str(v)


# ==========================================================
# SLOT EXTRACTION (RULE-BASED NLU)
# ==========================================================
def extract_budget(text: str) -> Optional[int]:
    """
    Extract maximum budget from user text.
    Examples:
      "budget 50000"
      "$50,000"
      "under 45000"
    """
    m = re.search(r"\$?\s*([\d,]{4,})", text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def extract_seats(text: str) -> Optional[int]:
    """
    Extract minimum seats from user text.
    Examples:
      "5 seats"
      "need 7 seat"
      "12 seater"
    Note:
      - This code interprets seats as MINIMUM requirement (>=)
    """
    m = re.search(r"(\d+)\s*(seat|seats|seater)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def extract_fuel(text: str) -> Optional[str]:
    """
    Extract fuel preference from user text.
    Supported values:
      diesel, gasoline, hybrid, ev, any
    Handles typos and punctuation.
    """
    t = (text or "").lower()

    # Normalize common typos/synonyms BEFORE removing punctuation
    t = (
        t.replace("disel", "diesel")
         .replace("gazoline", "gasoline")
         .replace("gasolin", "gasoline")
         .replace("petrol", "gasoline")
         .replace("benzine", "gasoline")
         .replace("hybird", "hybrid")
         .replace("hybird", "hybrid")
         .replace("electic", "ev")
         .replace("electric", "ev")
         .replace("electrical", "ev")
    )

    # Remove punctuation and normalize spaces
    t = re.sub(r"[^a-z0-9\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Direct checks (reliable)
    if "any" in t:
        return "any"
    if "diesel" in t:
        return "diesel"
    if "gasoline" in t or re.search(r"\bgas\b", t):
        return "gasoline"
    if "hybrid" in t or re.search(r"\bhev\b", t):
        return "hybrid"
    if re.search(r"\bev\b", t):
        return "ev"

    return None


# ==========================================================
# INTENT DETECTION (QUERY ROUTING)
# ==========================================================
def looks_like_question(text: str) -> bool:
    t = text.lower().strip()
    if "?" in t:
        return True

    starters = (
        "does ", "do ", "is ", "are ",
        "what ", "which ", "tell me", "can you", "have "
    )
    return t.startswith(starters)


def parse_constraints(text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    return extract_budget(text), extract_seats(text), extract_fuel(text)


# ==========================================================
# SLOT FILLING (DIALOG MANAGEMENT)
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
# DETERMINISTIC FILTERING (STRUCTURED RETRIEVAL)
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

        # Seats constraint only enforced when seats is known.
        # If seats is missing => keep as possible match.
        if seats is not None and seats < min_seats:
            continue

        if fuel != "any" and row_fuel != fuel:
            continue

        res.append(r)

    return sorted(res, key=lambda x: to_int(x.get("price_usd")) or 0, reverse=True)


# ==========================================================
# VECTOR DATABASE (DENSE RETRIEVAL)
# ==========================================================
def connect_chroma():
    client = chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(COLLECTION_NAME)


def retrieve_context(collection, query, target, top_k=4):
    res = collection.query(
        query_texts=[query],
        where={"brand": target["brand"], "model": target["model"]},
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    return res["documents"][0], res["metadatas"][0]


# ==========================================================
# MODEL RESOLUTION (WHICH CAR IS USER ASKING ABOUT?)
# ==========================================================
def pick_target_model(text, candidates):
    t = text.lower()
    for c in candidates:
        model = (c.get("model") or "").lower()
        if model and model in t:
            return c
    return None


def find_model_global(rows, text):
    t = text.lower()
    return [r for r in rows if (r.get("model") or "").lower() in t]


# ==========================================================
# EXTRACTIVE QUESTION ANSWERING (NO LLM)
# ==========================================================
def answer_from_context(question, docs):
    if not docs:
        return "I do not have that information in the provided official data."

    ctx = "\n".join(docs)

    patterns = [
        ("Reverse camera", r"Reverse camera\s*:\s*(.+)"),
        ("Turning radius", r"Minimum turning radius\s*:\s*(.+)"),
        ("Fold-up seats", r"Fold-up.*seat.*:\s*(.+)"),
    ]

    answers = []
    for label, p in patterns:
        m = re.search(p, ctx, re.IGNORECASE)
        if m:
            answers.append(f"{label}: {m.group(1).strip()}")

    if answers:
        return "From official specs:\n- " + "\n- ".join(answers)

    return "I found related information, but not an exact specification line."


# ==========================================================
# MAIN CHAT LOOP (STATE MACHINE)
# ==========================================================
def main():
    rows = load_min_table()
    collection = connect_chroma()

    slots = {"max_budget": None, "min_seats": None, "fuel": None}
    candidates = []

    print("Car Chatbot (Slot Filling + CSV Filter + RAG Q&A)")
    print("Type 'exit' to quit. Type 'new' to restart.\n")

    while True:
        user = input("You: ").strip()

        if user.lower() in {"exit", "quit"}:
            break

        if user.lower() in {"new", "restart"}:
            slots = {"max_budget": None, "min_seats": None, "fuel": None}
            candidates = []
            print("\nBot: OK, tell me your budget, seats, and fuel.\n")
            continue

        # ---------------- Q&A MODE ----------------
        if looks_like_question(user):
            global_matches = find_model_global(rows, user)
            target = pick_target_model(user, candidates) or (global_matches[0] if global_matches else None)

            if not target:
                print("\nBot: Please specify which model you mean.\n")
                continue

            docs, metas = retrieve_context(collection, user, target)
            print(f"\nBot: {answer_from_context(user, docs)}")

            if metas and metas[0].get("url"):
                print(f"Source: {metas[0]['url']}\n")
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

        print("Bot: You can now ask technical questions about these models.\n")


if __name__ == "__main__":
    main()


