from __future__ import annotations

import argparse
import csv
import inspect
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from scripts import chat_assistant
from scripts.chat_assistant import build_rag_engine, build_preowned_engine, chat_turn

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PREOWNED = PROJECT_ROOT / "data_preowned" / "csv_preowned" / "preowned_master.csv"
DEFAULT_TESTS_JSON = PROJECT_ROOT / "tests" / "qa_tests.json"


TEST_QUESTIONS = [
    "hello",
    "thanks",
    "/reset",
    "price of yaris cross gasoline",
    "how much is fortuner legender",
    "starting price of raize",
    "specs of fortuner legender",
    "show specs for veloz",
    "specs?",
    "summary of raize",
    "give me summary for corolla cross hev",
    "summary?",
    "does corolla cross have 360 camera",
    "does yaris cross have apple carplay",
    "what is the transmission of veloz",
    "what is the fuel type of land cruiser 250 diesel",
    "what is the seat number of hiace 16 seater",
    "price of it",
    "what about specs",
    "does it have 360 camera",
    "compare veloz vs vios",
    "vios vs raize",
    "compare",
    "recommend suv",
    "i want to buy a new car",
    "recommend SUV under $45000 gasoline",
    "budget 40000 fuel gasoline body suv",
    "budget 35000 body sedan fuel gasoline",
    "budget 60000 body suv fuel diesel min seats 7",
    "recommend pickup",
    "budget 50000",
    "diesel",
    "pickup",
    "recommend suv under 45000 gasoline",
    "both",
    "Fortuner Legender preowned price year mileage",
    "Veloz preowned price",
    "Yaris Cross used price",
    "pre-owned corolla cross hybrid year mileage",
    "show me listings for raize preowned",
    "preowned plate number fortuner",
    "certified pre-owned veloz 2024 mileage",
    "preowned yaris cross",
    "used fortuner legender",
    "mileage of preowned veloz",
    "does raize have sunroof panoramic and ventilated seat",
    "what is the 0-100 acceleration of vios",
    "tell me the best car in cambodia overall",
    "1) price of yaris cross",
    "\"specs of    fortuner    legender  \"",
    "(summary of raize)",
    "compare    veloz   versus   vios",
]


@dataclass
class TestCase:
    id: str
    q: str
    expected_pipeline: str  # optional, can be empty


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


def _find_official_master_dataset(user_path: Optional[str]) -> Path:
    candidates: List[Path] = []
    if user_path:
        candidates.append(Path(user_path))

    candidates += [
        PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv",
        PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv",
        PROJECT_ROOT / "data" / "csv" / "master.csv",
        PROJECT_ROOT / "data" / "csv" / "toyota_master.csv",
        PROJECT_ROOT / "data" / "processed" / "master.csv",
        PROJECT_ROOT / "data" / "processed" / "toyota_master.csv",
        PROJECT_ROOT / "data" / "master.csv",
        PROJECT_ROOT / "master.csv",
        PROJECT_ROOT / "data" / "jsonl" / "master.jsonl",
        PROJECT_ROOT / "data" / "processed" / "master.jsonl",
        PROJECT_ROOT / "master.jsonl",
    ]

    for p in candidates:
        if p.exists():
            return p

    tried = "\n".join([f"- {str(p)}" for p in candidates])
    raise FileNotFoundError(
        "Cannot find official master dataset file (CSV/JSONL).\n"
        "Tried these locations:\n"
        f"{tried}\n\n"
        "Fix:\n"
        '  python scripts/qa_runner_auto.py --official "/full/path/to/vehicle_master.csv"\n'
    )


def _load_full_rows(official_path: Path) -> List[Dict[str, Any]]:
    suf = official_path.suffix.lower()
    if suf == ".csv":
        return _read_rows_from_csv(official_path)
    if suf == ".jsonl":
        return _read_rows_from_jsonl(official_path)
    raise ValueError(f"Unsupported official dataset format: {official_path}")


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
        "remarks",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_json(out_path: Path, obj: Any) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_tests_json(path: Path) -> List[TestCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: List[TestCase] = []
    for i, r in enumerate(raw, start=1):
        q = str(r.get("q") or "").strip()
        if not q:
            continue
        out.append(
            TestCase(
                id=str(r.get("id") or f"T{i:03d}"),
                q=q,
                expected_pipeline=str(r.get("expected_pipeline") or "").strip(),
            )
        )
    return out


def _safe_call_chat_turn(
    q: str,
    state: Dict[str, Any],
    full_rows: List[Dict[str, Any]],
    rag_engine: Any,
    preowned_engine: Any,
    debug: bool,
) -> Dict[str, Any]:
    fn = chat_assistant.chat_turn
    sig = inspect.signature(fn)

    # Build positional args in the correct order
    # Always pass the first 4 core args first
    args: List[Any] = [q, state, full_rows, rag_engine]
    kwargs: Dict[str, Any] = {}

    params = list(sig.parameters.values())

    # Remaining parameters after the first 4
    for p in params[4:]:
        name = p.name

        if name in ("preowned_engine", "preowned"):
            # Some versions want it as positional, others accept keyword.
            # If it's positional-only or has no default, pass as positional.
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD) and p.default is inspect._empty:
                args.append(preowned_engine)
            else:
                kwargs[name] = preowned_engine

        elif name == "debug":
            # debug usually keyword-friendly
            kwargs["debug"] = debug

        else:
            # If it's required and we don't know it -> raise early with a clear message
            if p.default is inspect._empty and p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                raise TypeError(f"chat_turn has unsupported required parameter: {name}")

    return fn(*args, **kwargs)

def _extract_pipeline(res: Dict[str, Any]) -> str:
    p = str(res.get("pipeline") or "").strip()
    return p if p else "UNKNOWN"


def _extract_answer(res: Dict[str, Any]) -> str:
    a = res.get("answer")
    if isinstance(a, str):
        return a.strip()
    t = res.get("text")
    if isinstance(t, str):
        return t.strip()
    return ""


def _extract_sources(res: Dict[str, Any]) -> List[str]:
    s = res.get("sources")
    if isinstance(s, list):
        return [str(x) for x in s if x]
    return []


def _evaluate(expected_pipeline: str, actual_pipeline: str, answer: str) -> Tuple[bool, str]:
    remarks: List[str] = []

    if expected_pipeline:
        if actual_pipeline != expected_pipeline:
            remarks.append(f"pipeline_mismatch expected={expected_pipeline} actual={actual_pipeline}")

    if not answer.strip():
        remarks.append("empty_answer")

    ok = len(remarks) == 0 if expected_pipeline else ("empty_answer" not in remarks)
    return ok, "; ".join(remarks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--official", default="", help="Path to official master CSV/JSONL (optional).")
    ap.add_argument("--preowned", default=str(DEFAULT_PREOWNED), help="Path to preowned_master.csv")
    ap.add_argument("--outdir", default=str(PROJECT_ROOT / "outputs"), help="Output folder")
    ap.add_argument("--limit", type=int, default=0, help="Run only first N tests (0 = all)")
    ap.add_argument("--debug", action="store_true", help="Enable debug if chat_turn supports it")

    ap.add_argument("--tests", default="", help="Path to JSON tests file (optional).")
    ap.add_argument("--comment", default="", help="Session comment (saved in report header).")
    args = ap.parse_args()

    session_id = "S" + uuid.uuid4().hex[:10].upper()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    official_path = _find_official_master_dataset(args.official if args.official else None)
    full_rows = _load_full_rows(official_path)

    rag = build_rag_engine(full_rows)
    preowned = build_preowned_engine(args.preowned)

    tests: List[TestCase] = []
    if args.tests:
        tests_path = Path(args.tests)
        tests = _load_tests_json(tests_path)
    else:
        tests = [TestCase(id=f"Q{i:03d}", q=q, expected_pipeline="") for i, q in enumerate(TEST_QUESTIONS, start=1)]

    if args.limit and args.limit > 0:
        tests = tests[: args.limit]

    outdir = Path(args.outdir)
    txt_path = outdir / f"qa_session_{session_id}_{now}.txt"
    csv_path = outdir / f"qa_session_{session_id}_{now}.csv"
    fail_json_path = outdir / f"qa_failures_{session_id}_{now}.json"

    state: Dict[str, Any] = {}

    report_lines: List[str] = []
    report_csv_rows: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    report_lines.append(f"SESSION_ID: {session_id}")
    report_lines.append(f"COMMENT: {args.comment}")
    report_lines.append(f"PROJECT_ROOT: {PROJECT_ROOT}")
    report_lines.append(f"OFFICIAL_DATASET: {official_path}")
    report_lines.append(f"PREOWNED_DATASET: {Path(args.preowned)}")
    if args.tests:
        report_lines.append(f"TESTS_FILE: {Path(args.tests)}")
    report_lines.append("")

    total = 0
    passed = 0

    for tc in tests:
        total += 1

        res = _safe_call_chat_turn(tc.q, state, full_rows, rag, preowned, debug=bool(args.debug))
        answer = _extract_answer(res)
        actual_pipeline = _extract_pipeline(res)
        sources = _extract_sources(res)
        sources_txt = ", ".join(sources)

        ok, remarks = _evaluate(tc.expected_pipeline, actual_pipeline, answer)
        status = "CORRECT" if ok else "INCORRECT"
        if ok:
            passed += 1

        # Console output: user ask -> bot answer
        if tc.expected_pipeline:
            print(f"[{status}] {tc.id} EXPECTED={tc.expected_pipeline} ACTUAL={actual_pipeline}")
        else:
            print(f"[{status}] {tc.id} ACTUAL={actual_pipeline}")
        print(f"Q: {tc.q}")
        print("A: " + (answer if answer else "(empty)"))
        if sources_txt:
            print(f"SOURCES: {sources_txt}")
        if remarks:
            print(f"REMARKS: {remarks}")
        print("-" * 80)

        report_lines.append(f"[{status}] {tc.id} EXPECTED={tc.expected_pipeline} ACTUAL={actual_pipeline}")
        report_lines.append(f"Q: {tc.q}")
        report_lines.append("A: " + (answer if answer else "(empty)"))
        if sources_txt:
            report_lines.append(f"SOURCES: {sources_txt}")
        if remarks:
            report_lines.append(f"REMARKS: {remarks}")
        report_lines.append("-" * 80)

        report_csv_rows.append(
            {
                "id": tc.id,
                "question": tc.q,
                "expected_pipeline": tc.expected_pipeline,
                "actual_pipeline": actual_pipeline,
                "ok": str(ok),
                "answer": answer,
                "sources": sources_txt,
                "remarks": remarks,
            }
        )

        if not ok:
            failures.append(
                {
                    "id": tc.id,
                    "q": tc.q,
                    "expected_pipeline": tc.expected_pipeline,
                    "actual_pipeline": actual_pipeline,
                    "remarks": remarks,
                    "answer": answer,
                    "sources": sources,
                }
            )

    report_lines.append("")
    report_lines.append("SUMMARY")
    report_lines.append(f"TOTAL: {total}")
    report_lines.append(f"PASSED: {passed}")
    report_lines.append(f"FAILED: {total - passed}")
    report_lines.append(f"PASS_RATE: {passed / total:.2%}" if total else "PASS_RATE: N/A")
    report_lines.append("")
    report_lines.append("NEXT")
    report_lines.append(f"- Failures JSON (send to me): {fail_json_path.name}")
    report_lines.append(f"- TXT report: {txt_path.name}")
    report_lines.append(f"- CSV report: {csv_path.name}")

    _write_report_txt(txt_path, report_lines)
    _write_report_csv(csv_path, report_csv_rows)
    _write_json(fail_json_path, failures)

    print(f"Saved: {txt_path}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {fail_json_path}")

    # Exit code: 0 pass, 2 fail
    return 0 if (total == passed) else 2


if __name__ == "__main__":
    raise SystemExit(main())