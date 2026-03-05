# # scripts/qa_run_80.py
#
# import sys
# import time
# import json
# from pathlib import Path
# from typing import Any, Dict, List, Tuple, Optional
#
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))
#
# from scripts.csv_engine import load_full_rows
# from scripts.chat_assistant import build_rag_engine, chat_turn, _reset_state
# from scripts.chat_assistant import build_preowned_engine
#
#
# QUESTIONS_80: List[Tuple[str, str]] = [
#     # A) Services RAG (1–20)
#     ("What service packages does Toyota Cambodia provide?", "RAG"),
#     ("What is included in Service A?", "RAG"),
#     ("What is included in Service B?", "RAG"),
#     ("What is included in Service C?", "RAG"),
#     ("What is included in Service D?", "RAG"),
#     ("How often should Service A be done?", "RAG"),
#     ("What is the service interval for Service B?", "RAG"),
#     ("What is the difference between Service A and Service B?", "RAG"),
#     ("What is the difference between Service C and Service D?", "RAG"),
#     ("What checks are included in Service A?", "RAG"),
#     ("How many points are checked in Service B?", "RAG"),
#     ("What is the price of Service A?", "RAG"),
#     ("What is the price of Service C?", "RAG"),
#     ("What is included in Toyota maintenance packages?", "RAG"),
#     ("Do Toyota service packages include oil replacement?", "RAG"),
#     ("Does Toyota Cambodia provide maintenance schedules?", "RAG"),
#     ("What is included in the OEM warranty?", "RAG"),
#     ("Does the warranty cover Toyota genuine parts?", "RAG"),
#     ("Where can I find Toyota servicing information?", "RAG"),
#     ("What maintenance services does Toyota Cambodia offer?", "RAG"),
#
#     # B) Vehicle Specs CSV (21–40)
#     ("What is the price of Yaris Cross?", "CSV_METHOD"),
#     ("What engine does Wigo use?", "CSV_METHOD"),
#     ("What transmission does Yaris Cross have?", "CSV_METHOD"),
#     ("What body type is Corolla Cross?", "CSV_METHOD"),
#     ("What fuel type does Raize use?", "CSV_METHOD"),
#     ("How many seats does Fortuner have?", "CSV_METHOD"),
#     ("What engine does Corolla Cross use?", "CSV_METHOD"),
#     ("What is the price of Vios?", "CSV_METHOD"),
#     ("What transmission does Wigo have?", "CSV_METHOD"),
#     ("What fuel type does Fortuner use?", "CSV_METHOD"),
#     ("What body type is Raize?", "CSV_METHOD"),
#     ("What engine is used in Veloz?", "CSV_METHOD"),
#     ("What is the price of Corolla Cross HEV?", "CSV_METHOD"),
#     ("What is the engine capacity of Yaris Cross?", "CSV_METHOD"),
#     ("What is the body type of Veloz?", "CSV_METHOD"),
#     ("What transmission is used in Vios?", "CSV_METHOD"),
#     ("What fuel type is used in Wigo?", "CSV_METHOD"),
#     ("What engine type is used in Raize?", "CSV_METHOD"),
#     ("What is the price of Fortuner?", "CSV_METHOD"),
#     ("What body type is Yaris Cross?", "CSV_METHOD"),
#
#     # C) Vehicle Comparison (41–55)
#     ("Compare Yaris Cross and Corolla Cross", "CSV_METHOD"),
#     ("Compare Raize vs Vios", "CSV_METHOD"),
#     ("Compare Fortuner vs Veloz", "CSV_METHOD"),
#     ("Compare Wigo vs Raize", "CSV_METHOD"),
#     ("Compare Yaris Cross vs Raize", "CSV_METHOD"),
#     ("Compare Corolla Cross vs Fortuner", "CSV_METHOD"),
#     ("Compare Vios vs Yaris Cross", "CSV_METHOD"),
#     ("Compare Veloz vs Fortuner", "CSV_METHOD"),
#     ("Compare Raize vs Corolla Cross", "CSV_METHOD"),
#     ("Compare Wigo vs Vios", "CSV_METHOD"),
#     ("Which is bigger, Fortuner or Corolla Cross?", "CSV_METHOD"),
#     ("Which has a hybrid engine, Yaris Cross or Raize?", "CSV_METHOD"),
#     ("Which car is more fuel efficient, Wigo or Fortuner?", "CSV_METHOD"),
#     ("Which SUV is cheaper, Raize or Corolla Cross?", "CSV_METHOD"),
#     ("Which model has a bigger engine, Vios or Fortuner?", "CSV_METHOD"),
#
#     # D) Recommendation (56–70)
#     ("Recommend a Toyota SUV under $40,000", "CSV_METHOD"),
#     ("Recommend a hybrid SUV", "CSV_METHOD"),
#     ("Recommend a 7-seater Toyota", "CSV_METHOD"),
#     ("Recommend a Toyota under $25,000", "CSV_METHOD"),
#     ("Recommend an SUV under $35,000", "CSV_METHOD"),
#     ("Recommend a family car", "CSV_METHOD"),
#     ("Recommend a hybrid vehicle", "CSV_METHOD"),
#     ("Recommend a Toyota for city driving", "CSV_METHOD"),
#     ("Recommend a fuel efficient Toyota", "CSV_METHOD"),
#     ("Recommend a Toyota SUV under $50,000", "CSV_METHOD"),
#     ("Recommend a Toyota under $30,000", "CSV_METHOD"),
#     ("Recommend a Toyota for a small family", "CSV_METHOD"),
#     ("Recommend a compact Toyota car", "CSV_METHOD"),
#     ("Recommend a Toyota with hybrid engine", "CSV_METHOD"),
#     ("Recommend the cheapest Toyota SUV", "CSV_METHOD"),
#
#     # E) Pre-owned Dataset (71–75)
#     ("Show pre-owned Corolla Cross", "PREOWNED_RAG"),
#     ("Show pre-owned Toyota SUV", "PREOWNED_RAG"),
#     ("Do you have used Yaris Cross?", "PREOWNED_RAG"),
#     ("Show used Toyota under $30,000", "PREOWNED_RAG"),
#     ("Find pre-owned Fortuner", "PREOWNED_RAG"),
#
#     # F) Edge / Robustness Tests (76–80)
#     ("hello", "SYSTEM"),
#     ("can you help me choose a car", "SYSTEM"),
#     ("what toyota models are available", "SYSTEM"),
#     ("tell me about toyota cambodia", "RAG"),
#     ("ehh ehh ahh yyaa", "SYSTEM"),
# ]
#
#
# def _get_pipeline(res: Dict[str, Any]) -> str:
#     p = (res.get("pipeline") or "").strip()
#     if p:
#         return p
#     # fallback mapping
#     at = (res.get("answer_type") or "").strip().lower()
#     if "preowned" in at:
#         return "PREOWNED_RAG"
#     if "rag" == at:
#         return "RAG"
#     if "csv" in at:
#         return "CSV_METHOD"
#     if "system" in at:
#         return "SYSTEM"
#     return "UNKNOWN"
#
#
# def _short(text: str, n: int = 120) -> str:
#     t = " ".join((text or "").split())
#     return t[:n] + ("..." if len(t) > n else "")
#
#
# def _fmt_ms(sec: float) -> str:
#     ms = int(round(sec * 1000.0))
#     return str(ms)
#
#
# def _print_table(rows: List[List[str]], headers: List[str]) -> None:
#     widths = [len(h) for h in headers]
#     for r in rows:
#         for i, v in enumerate(r):
#             widths[i] = max(widths[i], len(v))
#
#     def line(sep: str = "-") -> str:
#         return "+".join(sep * (w + 2) for w in widths)
#
#     def fmt_row(r: List[str]) -> str:
#         out = []
#         for i, v in enumerate(r):
#             out.append(" " + v.ljust(widths[i]) + " ")
#         return "|".join(out)
#
#     print(line("-"))
#     print(fmt_row(headers))
#     print(line("="))
#     for r in rows:
#         print(fmt_row(r))
#     print(line("-"))
#
#
# def run(
#     preowned_csv_path: Optional[str] = None,
#     limit: Optional[int] = None,
#     sleep_s: float = 0.0,
#     save_jsonl: bool = True,
# ) -> None:
#     full_rows = load_full_rows()
#     rag = build_rag_engine(full_rows)
#
#     if preowned_csv_path:
#         preowned = build_preowned_engine(preowned_csv_path)
#     else:
#         preowned = build_preowned_engine(None)
#
#     state: Dict[str, Any] = {}
#     _reset_state(state)
#
#     out_rows: List[List[str]] = []
#     results_jsonl: List[Dict[str, Any]] = []
#
#     total = 0
#     correct = 0
#
#     items = QUESTIONS_80[: (limit or len(QUESTIONS_80))]
#
#     for idx, (q, expected) in enumerate(items, start=1):
#         if sleep_s > 0:
#             time.sleep(sleep_s)
#
#         t0 = time.perf_counter()
#         res = chat_turn(q, state, full_rows, rag, preowned, debug=False)
#         dt = time.perf_counter() - t0
#
#         actual = _get_pipeline(res)
#         ok = "Y" if actual == expected else "N"
#
#         total += 1
#         if ok == "Y":
#             correct += 1
#
#         text = str(res.get("text") or res.get("answer") or "")
#         sources = res.get("sources") or []
#         nsrc = str(len([s for s in sources if s]))
#
#         out_rows.append(
#             [
#                 str(idx),
#                 expected,
#                 actual,
#                 ok,
#                 _fmt_ms(dt),
#                 nsrc,
#                 _short(q, 60),
#                 _short(text, 90),
#             ]
#         )
#
#         results_jsonl.append(
#             {
#                 "i": idx,
#                 "question": q,
#                 "expected_pipeline": expected,
#                 "actual_pipeline": actual,
#                 "ok": ok == "Y",
#                 "latency_ms": int(round(dt * 1000)),
#                 "sources": sources,
#                 "answer_type": res.get("answer_type"),
#                 "text": text,
#             }
#         )
#
#     acc = (correct / total * 100.0) if total else 0.0
#     print(f"Total: {total} | Correct: {correct} | Accuracy: {acc:.2f}%")
#
#     headers = ["#", "Expected", "Actual", "OK", "ms", "Src", "Question", "Answer"]
#     _print_table(out_rows, headers)
#
#     if save_jsonl:
#         out_path = PROJECT_ROOT / "tests" / "qa_results_80.jsonl"
#         out_path.parent.mkdir(parents=True, exist_ok=True)
#         with out_path.open("w", encoding="utf-8") as f:
#             for r in results_jsonl:
#                 f.write(json.dumps(r, ensure_ascii=False) + "\n")
#         print(f"Saved: {out_path}")
#
#
# if __name__ == "__main__":
#     # Update this path to your real preowned CSV
#     PREOWNED_CSV = "/Users/sophea/My Document/RUPP_MITE/My Thesis Project/Final Project/Development/04-02 Chatbot/Chat-04-Feb 2/data_preowned/csv_preowned/preowned_master.csv"
#
#     # limit=None runs all 80
#     run(preowned_csv_path=PREOWNED_CSV, limit=None, sleep_s=0.0, save_jsonl=True)

# scripts/qa_run_80.py

import sys
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.csv_engine import load_full_rows
from scripts.chat_assistant import build_rag_engine, chat_turn, _reset_state
from scripts.chat_assistant import build_preowned_engine


QUESTIONS_80: List[Tuple[str, str]] = [
    # A) Services RAG (1–20)
    ("What service packages does Toyota Cambodia provide?", "RAG"),
    ("What is included in Service A?", "RAG"),
    ("What is included in Service B?", "RAG"),
    ("What is included in Service C?", "RAG"),
    ("What is included in Service D?", "RAG"),
    ("How often should Service A be done?", "RAG"),
    ("What is the service interval for Service B?", "RAG"),
    ("What is the difference between Service A and Service B?", "RAG"),
    ("What is the difference between Service C and Service D?", "RAG"),
    ("What checks are included in Service A?", "RAG"),
    ("How many points are checked in Service B?", "RAG"),
    ("What is the price of Service A?", "RAG"),
    ("What is the price of Service C?", "RAG"),
    ("What is included in Toyota maintenance packages?", "RAG"),
    ("Do Toyota service packages include oil replacement?", "RAG"),
    ("Does Toyota Cambodia provide maintenance schedules?", "RAG"),
    ("What is included in the OEM warranty?", "RAG"),
    ("Does the warranty cover Toyota genuine parts?", "RAG"),
    ("Where can I find Toyota servicing information?", "RAG"),
    ("What maintenance services does Toyota Cambodia offer?", "RAG"),

    # B) Vehicle Specs CSV (21–40)
    ("What is the price of Yaris Cross?", "CSV_METHOD"),
    ("What engine does Wigo use?", "CSV_METHOD"),
    ("What transmission does Yaris Cross have?", "CSV_METHOD"),
    ("What body type is Corolla Cross?", "CSV_METHOD"),
    ("What fuel type does Raize use?", "CSV_METHOD"),
    ("How many seats does Fortuner have?", "CSV_METHOD"),
    ("What engine does Corolla Cross use?", "CSV_METHOD"),
    ("What is the price of Vios?", "CSV_METHOD"),
    ("What transmission does Wigo have?", "CSV_METHOD"),
    ("What fuel type does Fortuner use?", "CSV_METHOD"),
    ("What body type is Raize?", "CSV_METHOD"),
    ("What engine is used in Veloz?", "CSV_METHOD"),
    ("What is the price of Corolla Cross HEV?", "CSV_METHOD"),
    ("What is the engine capacity of Yaris Cross?", "CSV_METHOD"),
    ("What is the body type of Veloz?", "CSV_METHOD"),
    ("What transmission is used in Vios?", "CSV_METHOD"),
    ("What fuel type is used in Wigo?", "CSV_METHOD"),
    ("What engine type is used in Raize?", "CSV_METHOD"),
    ("What is the price of Fortuner?", "CSV_METHOD"),
    ("What body type is Yaris Cross?", "CSV_METHOD"),

    # C) Vehicle Comparison (41–55)
    ("Compare Yaris Cross and Corolla Cross", "CSV_METHOD"),
    ("Compare Raize vs Vios", "CSV_METHOD"),
    ("Compare Fortuner vs Veloz", "CSV_METHOD"),
    ("Compare Wigo vs Raize", "CSV_METHOD"),
    ("Compare Yaris Cross vs Raize", "CSV_METHOD"),
    ("Compare Corolla Cross vs Fortuner", "CSV_METHOD"),
    ("Compare Vios vs Yaris Cross", "CSV_METHOD"),
    ("Compare Veloz vs Fortuner", "CSV_METHOD"),
    ("Compare Raize vs Corolla Cross", "CSV_METHOD"),
    ("Compare Wigo vs Vios", "CSV_METHOD"),
    ("Which is bigger, Fortuner or Corolla Cross?", "CSV_METHOD"),
    ("Which has a hybrid engine, Yaris Cross or Raize?", "CSV_METHOD"),
    ("Which car is more fuel efficient, Wigo or Fortuner?", "CSV_METHOD"),
    ("Which SUV is cheaper, Raize or Corolla Cross?", "CSV_METHOD"),
    ("Which model has a bigger engine, Vios or Fortuner?", "CSV_METHOD"),

    # D) Recommendation (56–70)
    ("Recommend a Toyota SUV under $40,000", "CSV_METHOD"),
    ("Recommend a hybrid SUV", "CSV_METHOD"),
    ("Recommend a 7-seater Toyota", "CSV_METHOD"),
    ("Recommend a Toyota under $25,000", "CSV_METHOD"),
    ("Recommend an SUV under $35,000", "CSV_METHOD"),
    ("Recommend a family car", "CSV_METHOD"),
    ("Recommend a hybrid vehicle", "CSV_METHOD"),
    ("Recommend a Toyota for city driving", "CSV_METHOD"),
    ("Recommend a fuel efficient Toyota", "CSV_METHOD"),
    ("Recommend a Toyota SUV under $50,000", "CSV_METHOD"),
    ("Recommend a Toyota under $30,000", "CSV_METHOD"),
    ("Recommend a Toyota for a small family", "CSV_METHOD"),
    ("Recommend a compact Toyota car", "CSV_METHOD"),
    ("Recommend a Toyota with hybrid engine", "CSV_METHOD"),
    ("Recommend the cheapest Toyota SUV", "CSV_METHOD"),

    # E) Pre-owned Dataset (71–75)
    ("Show pre-owned Corolla Cross", "PREOWNED_RAG"),
    ("Show pre-owned Toyota SUV", "PREOWNED_RAG"),
    ("Do you have used Yaris Cross?", "PREOWNED_RAG"),
    ("Show used Toyota under $30,000", "PREOWNED_RAG"),
    ("Find pre-owned Fortuner", "PREOWNED_RAG"),

    # F) Edge / Robustness Tests (76–80)
    ("hello", "SYSTEM"),
    ("can you help me choose a car", "SYSTEM"),
    ("what toyota models are available", "SYSTEM"),
    ("tell me about toyota cambodia", "RAG"),
    ("ehh ehh ahh yyaa", "SYSTEM"),
]


def _get_pipeline(res: Dict[str, Any]) -> str:
    p = (res.get("pipeline") or "").strip()
    if p:
        return p
    at = (res.get("answer_type") or "").strip().lower()
    if "preowned" in at:
        return "PREOWNED_RAG"
    if at == "rag":
        return "RAG"
    if "csv" in at:
        return "CSV_METHOD"
    if "system" in at:
        return "SYSTEM"
    return "UNKNOWN"


def _short(text: str, n: int = 120) -> str:
    t = " ".join((text or "").split())
    return t[:n] + ("..." if len(t) > n else "")


def _fmt_ms(sec: float) -> str:
    return str(int(round(sec * 1000.0)))


def _print_table(rows: List[List[str]], headers: List[str]) -> None:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(v))

    def line(sep: str = "-") -> str:
        return "+".join(sep * (w + 2) for w in widths)

    def fmt_row(r: List[str]) -> str:
        out = []
        for i, v in enumerate(r):
            out.append(" " + v.ljust(widths[i]) + " ")
        return "|".join(out)

    print(line("-"))
    print(fmt_row(headers))
    print(line("="))
    for r in rows:
        print(fmt_row(r))
    print(line("-"))


def _enable_vehicle_rag_profiler(rag_engine: Any) -> None:
    """
    Composite rag_engine has .vehicle and .services in your build_rag_engine().
    But to be safe, we detect common shapes.
    """
    # If composite object stores engines as attributes:
    for attr in ("vehicle", "vehicle_engine", "_vehicle", "vehicle_rag", "veh"):
        if hasattr(rag_engine, attr):
            eng = getattr(rag_engine, attr)
            if eng is not None:
                _attach_profiler_if_vehicle(eng)

    # If composite is a class with closure, we can't access. In that case, do nothing.


def _attach_profiler_if_vehicle(engine: Any) -> None:
    """
    Monkey-patch VehicleRAGEngine.rag_answer to store breakdown in engine._prof
    without changing your source files.
    """
    if engine is None:
        return
    if getattr(engine, "_prof_enabled", False):
        return

    if not hasattr(engine, "rag_answer"):
        return

    orig = engine.rag_answer

    def wrapped(question: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
        prof: Dict[str, float] = {}
        t_all = time.perf_counter()

        # resolve_target
        t = time.perf_counter()
        target = None
        if hasattr(engine, "resolve_target"):
            target = engine.resolve_target(question, last_model_norm)
        prof["resolve_target_ms"] = (time.perf_counter() - t) * 1000.0

        if not target:
            out = orig(question, last_model_norm=last_model_norm)
            prof["total_vehicle_rag_ms"] = (time.perf_counter() - t_all) * 1000.0
            engine._prof = prof
            return out

        # vector + keyword + fuse
        docs = []
        metas = []

        if hasattr(engine, "_hybrid_retrieve"):
            t = time.perf_counter()
            # _hybrid_retrieve signature in my optimized version:
            # _hybrid_retrieve(query, target, top_k_final)
            try:
                docs, metas = engine._hybrid_retrieve(question, target, getattr(engine, "top_k_final", 4))
            except TypeError:
                # fallback if older signature exists
                docs, metas = engine._hybrid_retrieve(question, target, 4)
            prof["hybrid_retrieve_ms"] = (time.perf_counter() - t) * 1000.0

        # prompt build
        t = time.perf_counter()
        if hasattr(engine, "_build_prompt"):
            prompt = engine._build_prompt(question, docs, metas)
        else:
            prompt = ""
        prof["prompt_build_ms"] = (time.perf_counter() - t) * 1000.0

        # ollama generate
        t = time.perf_counter()
        if hasattr(engine, "_ollama_generate"):
            _ = engine._ollama_generate(prompt)
        prof["ollama_generate_ms"] = (time.perf_counter() - t) * 1000.0

        # call original for real output (keeps behavior the same)
        out = orig(question, last_model_norm=last_model_norm)

        prof["total_vehicle_rag_ms"] = (time.perf_counter() - t_all) * 1000.0
        engine._prof = prof
        return out

    engine.rag_answer = wrapped
    engine._prof_enabled = True


def run(
    preowned_csv_path: Optional[str] = None,
    limit: Optional[int] = None,
    sleep_s: float = 0.0,
    save_jsonl: bool = True,
) -> None:
    full_rows = load_full_rows()
    rag = build_rag_engine(full_rows)

    # Try to enable profiler (best-effort)
    _enable_vehicle_rag_profiler(rag)

    preowned = build_preowned_engine(preowned_csv_path) if preowned_csv_path else build_preowned_engine(None)

    state: Dict[str, Any] = {}
    _reset_state(state)

    out_rows: List[List[str]] = []
    results_jsonl: List[Dict[str, Any]] = []

    total = 0
    correct = 0

    items = QUESTIONS_80[: (limit or len(QUESTIONS_80))]

    for idx, (q, expected) in enumerate(items, start=1):
        if sleep_s > 0:
            time.sleep(sleep_s)

        t0 = time.perf_counter()
        res = chat_turn(q, state, full_rows, rag, preowned, debug=False)
        dt = time.perf_counter() - t0

        actual = _get_pipeline(res)
        ok = "Y" if actual == expected else "N"

        total += 1
        if ok == "Y":
            correct += 1

        text = str(res.get("text") or res.get("answer") or "")
        sources = res.get("sources") or []
        nsrc = str(len([s for s in sources if s]))

        # Read profiler if present (vehicle engine only)
        prof = {}
        # If composite exposes vehicle engine, show it; otherwise blank.
        vehicle_eng = None
        for attr in ("vehicle", "vehicle_engine", "_vehicle", "vehicle_rag", "veh"):
            if hasattr(rag, attr):
                vehicle_eng = getattr(rag, attr)
                break
        if vehicle_eng is not None and hasattr(vehicle_eng, "_prof"):
            prof = getattr(vehicle_eng, "_prof") or {}

        out_rows.append(
            [
                str(idx),
                expected,
                actual,
                ok,
                _fmt_ms(dt),
                nsrc,
                _fmt_ms((prof.get("resolve_target_ms", 0.0)) / 1000.0) if prof else "",
                _fmt_ms((prof.get("hybrid_retrieve_ms", 0.0)) / 1000.0) if prof else "",
                _fmt_ms((prof.get("prompt_build_ms", 0.0)) / 1000.0) if prof else "",
                _fmt_ms((prof.get("ollama_generate_ms", 0.0)) / 1000.0) if prof else "",
                _short(q, 50),
            ]
        )

        results_jsonl.append(
            {
                "i": idx,
                "question": q,
                "expected_pipeline": expected,
                "actual_pipeline": actual,
                "ok": ok == "Y",
                "latency_ms": int(round(dt * 1000)),
                "sources": sources,
                "answer_type": res.get("answer_type"),
                "text": text,
                "prof": prof,
            }
        )

    acc = (correct / total * 100.0) if total else 0.0
    print(f"Total: {total} | Correct: {correct} | Accuracy: {acc:.2f}%")

    headers = ["#", "Expected", "Actual", "OK", "ms", "Src", "tgt", "retr", "prmpt", "llm", "Question"]
    _print_table(out_rows, headers)

    if save_jsonl:
        out_path = PROJECT_ROOT / "tests" / "qa_results_80.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for r in results_jsonl:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    PREOWNED_CSV = "/Users/sophea/My Document/RUPP_MITE/My Thesis Project/Final Project/Development/04-02 Chatbot/Chat-04-Feb 2/data_preowned/csv_preowned/preowned_master.csv"
    run(preowned_csv_path=PREOWNED_CSV, limit=None, sleep_s=0.0, save_jsonl=True)


