from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = PROJECT_ROOT / "data_services" / "json_services"
DOCS_DIR = PROJECT_ROOT / "data_services" / "docs_services"

DOCS_DIR.mkdir(parents=True, exist_ok=True)

def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _flatten(obj: Any) -> List[str]:
    out: List[str] = []

    if obj is None:
        return out

    if isinstance(obj, str):
        s = obj.strip()
        if s:
            out.append(s)
        return out

    if isinstance(obj, (int, float, bool)):
        out.append(str(obj))
        return out

    if isinstance(obj, list):
        for x in obj:
            out.extend(_flatten(x))
        return out

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (str, int, float, bool)) and str(v).strip():
                out.append(f"{k}: {str(v).strip()}")
            else:
                nested = _flatten(v)
                if nested:
                    out.append(f"{k}:")
                    out.extend([f"- {line}" for line in nested])
        return out

    return out

def main() -> None:
    json_files = sorted(JSON_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in: {JSON_DIR}")
        return

    for jf in json_files:
        data = _read_json(jf)
        lines = _flatten(data)

        title = jf.stem.replace("-", " ").strip().title()
        text = "\n".join([f"Title: {title}", "", *lines]).strip() + "\n"

        out_path = DOCS_DIR / f"{jf.stem}.txt"
        out_path.write_text(text, encoding="utf-8")
        print(f"Wrote: {out_path}")

if __name__ == "__main__":
    main()