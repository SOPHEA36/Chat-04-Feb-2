# from __future__ import annotations
#
# import argparse
# import csv
# import json
# import inspect
# from datetime import datetime
# from pathlib import Path
# from typing import Any, Dict, List, Optional, Tuple
#
# import pandas as pd
#
# from scripts.chat_assistant import build_rag_engine, build_preowned_engine, chat_turn
#
#
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
#
#
# def _read_rows_from_csv(path: Path) -> List[Dict[str, Any]]:
#     df = pd.read_csv(path)
#     df = df.fillna("")
#     return df.to_dict(orient="records")
#
#
# def _read_rows_from_jsonl(path: Path) -> List[Dict[str, Any]]:
#     rows: List[Dict[str, Any]] = []
#     with path.open("r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             rows.append(json.loads(line))
#     return rows
#
#
# def _find_official_master_dataset(user_path: Optional[str]) -> Path:
#     candidates: List[Path] = []
#     if user_path:
#         candidates.append(Path(user_path))
#
#     candidates += [
#         PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv",
#         PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv",
#         PROJECT_ROOT / "data" / "csv" / "master.csv",
#         PROJECT_ROOT / "data" / "csv" / "toyota_master.csv",
#         PROJECT_ROOT / "data" / "processed" / "master.csv",
#         PROJECT_ROOT / "data" / "processed" / "toyota_master.csv",
#         PROJECT_ROOT / "data" / "master.csv",
#         PROJECT_ROOT / "master.csv",
#         PROJECT_ROOT / "data" / "jsonl" / "master.jsonl",
#         PROJECT_ROOT / "data" / "processed" / "master.jsonl",
#         PROJECT_ROOT / "master.jsonl",
#     ]
#
#     for p in candidates:
#         if p.exists():
#             return p
#
#     tried = "\n".join([f"- {str(p)}" for p in candidates])
#     raise FileNotFoundError(
#         "Cannot find official master dataset file (CSV/JSONL).\n"
#         "Tried these locations:\n"
#         f"{tried}\n\n"
#         "Fix:\n"
#         "  python scripts/qa_runner_from_json.py --official \"/full/path/to/vehicle_master.csv\""
#     )
#
#
# def _load_full_rows(official_path: Path) -> List[Dict[str, Any]]:
#     if official_path.suffix.lower() == ".csv":
#         return _read_rows_from_csv(official_path)
#     if official_path.suffix.lower() == ".jsonl":
#         return _read_rows_from_jsonl(official_path)
#     raise ValueError(f"Unsupported official dataset format: {official_path}")
#
#
# def _load_tests_json(path: Path) -> List[Dict[str, str]]:
#     data = json.loads(path.read_text(encoding="utf-8"))
#     if not isinstance(data, list):
#         raise ValueError("qa_tests_200.json must be a JSON array of objects.")
#     out: List[Dict[str, str]] = []
#     for item in data:
#         if not isinstance(item, dict):
#             continue
#         q = str(item.get("q") or "").strip()
#         ep = str(item.get("expected_pipeline") or "").strip()
#         if q and ep:
#             out.append({"q": q, "expected_pipeline": ep})
#     return out
#
#
# def _safe_pipeline_name(raw: Any) -> str:
#     if raw is None:
#         return ""
#     return str(raw).strip()
#
#
# def _normalize_pipeline(p: str) -> str:
#     p = (p or "").strip().upper()
#     aliases = {
#         "RAG_SERVICES": "RAG",
#         "SERVICES_RAG": "RAG",
#         "RAG_SERVICE": "RAG",
#         "PREOWNED": "PREOWNED_RAG",
#         "PREOWNED_RAG_ENGINE": "PREOWNED_RAG",
#         "CSV": "CSV_METHOD",
#         "CSV_ENGINE": "CSV_METHOD",
#         "RECOMMENDATION": "CSV_METHOD",
#     }
#     return aliases.get(p, p)
#
#
# def _call_chat_turn(
#     question: str,
#     state: Dict[str, Any],
#     full_rows: List[Dict[str, Any]],
#     rag_engine: Any,
#     preowned_engine: Any,
#     debug: bool,
# ) -> Dict[str, Any]:
#     sig = inspect.signature(chat_turn)
#     params = set(sig.parameters.keys())
#
#     kwargs: Dict[str, Any] = {}
#     if "debug" in params:
#         kwargs["debug"] = debug
#
#     if "preowned" in params:
#         kwargs["preowned"] = preowned_engine
#     elif "preowned_engine" in params:
#         kwargs["preowned_engine"] = preowned_engine
#
#     return chat_turn(question, state, full_rows, rag_engine, **kwargs)
#
#
# def _write_report_txt(out_path: Path, lines: List[str]) -> None:
#     out_path.parent.mkdir(parents=True, exist_ok=True)
#     out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
#
#
# def _write_report_csv(out_path: Path, rows: List[Dict[str, Any]]) -> None:
#     out_path.parent.mkdir(parents=True, exist_ok=True)
#     fieldnames = [
#         "id",
#         "question",
#         "expected_pipeline",
#         "actual_pipeline",
#         "ok",
#         "answer",
#         "sources",
#     ]
#     with out_path.open("w", newline="", encoding="utf-8") as f:
#         w = csv.DictWriter(f, fieldnames=fieldnames)
#         w.writeheader()
#         for r in rows:
#             w.writerow(r)
#
#
# def main() -> int:
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--tests", default=str(PROJECT_ROOT / "tests" / "qa_tests_200.json"), help="Path to qa_tests_200.json")
#     ap.add_argument("--official", default="", help="Path to official vehicle master CSV/JSONL (optional).")
#     ap.add_argument(
#         "--preowned",
#         default=str(PROJECT_ROOT / "data_preowned" / "csv_preowned" / "preowned_master.csv"),
#         help="Path to preowned_master.csv",
#     )
#     ap.add_argument("--outdir", default=str(PROJECT_ROOT / "outputs"), help="Output folder")
#     ap.add_argument("--limit", type=int, default=0, help="Run only first N tests (0 = all)")
#     ap.add_argument("--debug", action="store_true", help="Enable debug in chat_turn if supported")
#     args = ap.parse_args()
#
#     tests_path = Path(args.tests)
#     tests = _load_tests_json(tests_path)
#
#     if args.limit and args.limit > 0:
#         tests = tests[: args.limit]
#
#     official_path = _find_official_master_dataset(args.official if args.official else None)
#     full_rows = _load_full_rows(official_path)
#
#     rag = build_rag_engine(full_rows)
#     preowned = build_preowned_engine(args.preowned)
#
#     state: Dict[str, Any] = {}
#
#     now = datetime.now().strftime("%Y%m%d_%H%M%S")
#     outdir = Path(args.outdir)
#     txt_path = outdir / f"qa_json_run_{now}.txt"
#     csv_path = outdir / f"qa_json_run_{now}.csv"
#
#     report_lines: List[str] = []
#     report_csv_rows: List[Dict[str, Any]] = []
#
#     report_lines.append(f"PROJECT_ROOT: {PROJECT_ROOT}")
#     report_lines.append(f"TESTS: {tests_path}")
#     report_lines.append(f"OFFICIAL_DATASET: {official_path}")
#     report_lines.append(f"PREOWNED_DATASET: {Path(args.preowned)}")
#     report_lines.append(f"chat_turn signature: {inspect.signature(chat_turn)}")
#     report_lines.append("")
#
#     failed = 0
#
#     for i, t in enumerate(tests, start=1):
#         test_id = f"T{i:03d}"
#         q = t["q"]
#         expected = _normalize_pipeline(t["expected_pipeline"])
#
#         res = _call_chat_turn(q, state, full_rows, rag, preowned, debug=bool(args.debug))
#
#         answer = str(res.get("answer") or res.get("text") or "").strip()
#         actual = _normalize_pipeline(_safe_pipeline_name(res.get("pipeline")))
#         sources = res.get("sources") or []
#         sources_txt = ", ".join([str(s) for s in sources if s])
#
#         ok = (actual == expected)
#         if not ok:
#             failed += 1
#
#         status = "CORRECT" if ok else "INCORRECT"
#         print(f"[{status}] {test_id} EXPECTED={expected} ACTUAL={actual}")
#         print(f"Q: {q}")
#         print(f"A: {answer if answer else '(empty)'}")
#         if sources_txt:
#             print(f"SOURCES: {sources_txt}")
#         print("-" * 80)
#
#         report_lines.append(f"ID: {test_id}")
#         report_lines.append(f"OK: {ok}")
#         report_lines.append(f"EXPECTED_PIPELINE: {expected}")
#         report_lines.append(f"ACTUAL_PIPELINE: {actual}")
#         report_lines.append(f"Q: {q}")
#         report_lines.append("ANSWER:")
#         report_lines.append(answer if answer else "(empty)")
#         if sources_txt:
#             report_lines.append(f"SOURCES: {sources_txt}")
#         report_lines.append("-" * 80)
#
#         report_csv_rows.append(
#             {
#                 "id": test_id,
#                 "question": q,
#                 "expected_pipeline": expected,
#                 "actual_pipeline": actual,
#                 "ok": ok,
#                 "answer": answer,
#                 "sources": sources_txt,
#             }
#         )
#
#     _write_report_txt(txt_path, report_lines)
#     _write_report_csv(csv_path, report_csv_rows)
#
#     print(f"Saved: {txt_path}")
#     print(f"Saved: {csv_path}")
#
#     if failed > 0:
#         print("Some tests failed. Open the TXT report and search for: 'OK: False'")
#         return 2
#
#     print("All tests passed.")
#     return 0
#
#
# if __name__ == "__main__":
#     raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
import inspect
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from scripts.chat_assistant import build_rag_engine, build_preowned_engine, chat_turn


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# =========================================================
# CONFIGURATION PATHS (EDIT HERE IF FILES MOVE)
# =========================================================

QA_TEST_FILE = PROJECT_ROOT / "tests" / "qa_tests_80.json"

OFFICIAL_DATASET_FILE = PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv"

PREOWNED_DATASET_FILE = PROJECT_ROOT / "data_preowned" / "csv_preowned" / "preowned_master.csv"

OUTPUT_FOLDER = PROJECT_ROOT / "outputs"


# =========================================================
# DATASET READERS
# =========================================================

def _read_rows_from_csv(path: Path) -> List[Dict[str, Any]]:
    df = pd.read_csv(path)
    df = df.fillna("")
    return df.to_dict(orient="records")


def _read_rows_from_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_full_rows(dataset_path: Path) -> List[Dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    if dataset_path.suffix.lower() == ".csv":
        return _read_rows_from_csv(dataset_path)

    if dataset_path.suffix.lower() == ".jsonl":
        return _read_rows_from_jsonl(dataset_path)

    raise ValueError(f"Unsupported dataset format: {dataset_path}")


# =========================================================
# LOAD TEST QUESTIONS
# =========================================================

def _load_tests_json(path: Path) -> List[Dict[str, str]]:
    """
    Load QA test file.

    Supports BOTH formats:

    OLD:
        { "q": "...", "expected_pipeline": "CSV_METHOD" }

    NEW:
        { "question": "...", "expected_pipeline": "CSV_METHOD" }
    """

    if not path.exists():
        raise FileNotFoundError(f"QA test file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("QA test JSON must be an array")

    out: List[Dict[str, str]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        # SUPPORT BOTH KEYS
        q = str(item.get("question") or item.get("q") or "").strip()
        ep = str(item.get("expected_pipeline") or "").strip()

        if not q or not ep:
            continue

        out.append(
            {
                "q": q,
                "expected_pipeline": ep
            }
        )

    return out


# =========================================================
# PIPELINE NORMALIZATION
# =========================================================

def _safe_pipeline_name(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip()


def _normalize_pipeline(p: str) -> str:
    p = (p or "").strip().upper()

    aliases = {
        "RAG_SERVICES": "RAG",
        "SERVICES_RAG": "RAG",
        "RAG_SERVICE": "RAG",

        "PREOWNED": "PREOWNED_RAG",
        "PREOWNED_RAG_ENGINE": "PREOWNED_RAG",

        "CSV": "CSV_METHOD",
        "CSV_ENGINE": "CSV_METHOD",
        "RECOMMENDATION": "CSV_METHOD",
    }

    return aliases.get(p, p)


# =========================================================
# SAFE CALL chat_turn()
# =========================================================

def _call_chat_turn(
    question: str,
    state: Dict[str, Any],
    full_rows: List[Dict[str, Any]],
    rag_engine: Any,
    preowned_engine: Any,
    debug: bool,
) -> Dict[str, Any]:

    sig = inspect.signature(chat_turn)
    params = set(sig.parameters.keys())

    kwargs: Dict[str, Any] = {}

    if "debug" in params:
        kwargs["debug"] = debug

    if "preowned" in params:
        kwargs["preowned"] = preowned_engine
    elif "preowned_engine" in params:
        kwargs["preowned_engine"] = preowned_engine

    return chat_turn(question, state, full_rows, rag_engine, **kwargs)


# =========================================================
# REPORT WRITERS
# =========================================================

def _write_report_txt(out_path: Path, lines: List[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_report_csv(out_path: Path, rows: List[Dict[str, Any]]) -> None:

    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "question",
        "expected_pipeline",
        "actual_pipeline",
        "ok",
        "answer",
        "sources",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:

        w = csv.DictWriter(f, fieldnames=fieldnames)

        w.writeheader()

        for r in rows:
            w.writerow(r)


# =========================================================
# MAIN
# =========================================================

def main() -> int:

    ap = argparse.ArgumentParser()

    # You can override these from CLI if needed
    ap.add_argument("--tests", default=str(QA_TEST_FILE))
    ap.add_argument("--official", default=str(OFFICIAL_DATASET_FILE))
    ap.add_argument("--preowned", default=str(PREOWNED_DATASET_FILE))
    ap.add_argument("--outdir", default=str(OUTPUT_FOLDER))

    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--debug", action="store_true")

    args = ap.parse_args()

    tests_path = Path(args.tests)

    tests = _load_tests_json(tests_path)

    if args.limit > 0:
        tests = tests[: args.limit]

    official_path = Path(args.official)

    full_rows = _load_full_rows(official_path)

    rag = build_rag_engine(full_rows)

    preowned = build_preowned_engine(args.preowned)

    state: Dict[str, Any] = {}

    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    outdir = Path(args.outdir)

    txt_path = outdir / f"qa_json_run_{now}.txt"

    csv_path = outdir / f"qa_json_run_{now}.csv"

    report_lines: List[str] = []

    report_csv_rows: List[Dict[str, Any]] = []

    report_lines.append(f"PROJECT_ROOT: {PROJECT_ROOT}")
    report_lines.append(f"TESTS: {tests_path}")
    report_lines.append(f"OFFICIAL_DATASET: {official_path}")
    report_lines.append(f"PREOWNED_DATASET: {Path(args.preowned)}")
    report_lines.append(f"chat_turn signature: {inspect.signature(chat_turn)}")
    report_lines.append("")

    failed = 0

    for i, t in enumerate(tests, start=1):

        test_id = f"T{i:03d}"

        q = t["q"]

        expected = _normalize_pipeline(t["expected_pipeline"])

        res = _call_chat_turn(q, state, full_rows, rag, preowned, debug=args.debug)

        answer = str(res.get("answer") or res.get("text") or "").strip()

        actual = _normalize_pipeline(_safe_pipeline_name(res.get("pipeline")))

        sources = res.get("sources") or []

        sources_txt = ", ".join([str(s) for s in sources if s])

        ok = actual == expected

        if not ok:
            failed += 1

        status = "CORRECT" if ok else "INCORRECT"

        print(f"[{status}] {test_id} EXPECTED={expected} ACTUAL={actual}")
        print(f"Q: {q}")
        print(f"A: {answer if answer else '(empty)'}")

        if sources_txt:
            print(f"SOURCES: {sources_txt}")

        print("-" * 80)

        report_lines.append(f"ID: {test_id}")
        report_lines.append(f"OK: {ok}")
        report_lines.append(f"EXPECTED_PIPELINE: {expected}")
        report_lines.append(f"ACTUAL_PIPELINE: {actual}")
        report_lines.append(f"Q: {q}")
        report_lines.append("ANSWER:")
        report_lines.append(answer if answer else "(empty)")

        if sources_txt:
            report_lines.append(f"SOURCES: {sources_txt}")

        report_lines.append("-" * 80)

        report_csv_rows.append(
            {
                "id": test_id,
                "question": q,
                "expected_pipeline": expected,
                "actual_pipeline": actual,
                "ok": ok,
                "answer": answer,
                "sources": sources_txt,
            }
        )

    _write_report_txt(txt_path, report_lines)

    _write_report_csv(csv_path, report_csv_rows)

    print(f"Saved: {txt_path}")
    print(f"Saved: {csv_path}")

    if failed > 0:
        print("Some tests failed. Check TXT report for details.")
        return 2

    print("All tests passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())



