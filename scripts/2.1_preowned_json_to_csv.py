import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JSON_DIR = PROJECT_ROOT / "data_preowned" / "json_preowned"
CSV_DIR = PROJECT_ROOT / "data_preowned" / "csv_preowned"
OUTPUT_CSV = CSV_DIR / "preowned_master.csv"


def to_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x)
    s = re.sub(r"[^\d]", "", str(x))
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace(",", "").strip()
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def norm_text(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def safe_load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))


def derive_plate_from_filename_or_url(fp: Path, source_url: str) -> str:
    # This captures full patterns like CAM-AYA-6336, PP-2BQ-6886, etc.
    text = f"{fp.stem} {source_url}"
    m = re.search(r"\b([A-Z]{2,4}-[A-Z0-9]{1,4}-[A-Z0-9]{2,6})\b", text.upper())
    if m:
        return m.group(1)
    return ""


def infer_fuel_from_engine(engine: str) -> str:
    s = (engine or "").lower()
    if "diesel" in s:
        return "diesel"
    if "hybrid" in s or "hev" in s:
        return "hybrid"
    if s:
        return "gasoline"
    return ""


def parse_one(fp: Path) -> Dict[str, Any]:
    raw = safe_load_json(fp)
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        raw = raw[0]

    if not isinstance(raw, dict):
        raise ValueError("JSON root is not a dict")

    details = raw.get("details") or {}
    if not isinstance(details, dict):
        details = {}

    source_url = norm_text(raw.get("source_url"))
    model = norm_text(raw.get("model"))
    brand = norm_text(raw.get("brand", "Toyota"))

    listing_id = fp.stem

    price_str = raw.get("price")  # e.g. "US$54,900"
    year = details.get("model_year")
    mileage = details.get("mileage")
    body_colour = details.get("body_colour") or details.get("color") or details.get("colour")
    body_type = details.get("body_type")
    engine = details.get("engine")
    transmission = details.get("transmission")
    fuel = details.get("fuel") or infer_fuel_from_engine(norm_text(engine))

    plate_no = details.get("plate_no") or derive_plate_from_filename_or_url(fp, source_url)

    row = {
        "listing_id": norm_text(listing_id),
        "type": norm_text(raw.get("type")),
        "brand": brand,
        "model": model,
        "price_usd": to_float(price_str),
        "year": to_int(year),
        "mileage_km": to_int(mileage),
        "body_color": norm_text(body_colour),
        "body_type": norm_text(body_type),
        "engine": norm_text(engine),
        "fuel": norm_text(fuel),
        "transmission": norm_text(transmission),
        "plate_no": norm_text(plate_no),
        "source_url": source_url,
        "source_json": str(fp),
    }

    return row


def main():
    if not JSON_DIR.exists():
        raise FileNotFoundError(f"JSON_DIR not found: {JSON_DIR}")

    files = sorted([p for p in JSON_DIR.rglob("*.json") if p.is_file()])
    if not files:
        raise FileNotFoundError(f"No JSON files found under: {JSON_DIR}")

    rows: List[Dict[str, Any]] = []
    errors: List[str] = []

    for fp in files:
        try:
            rows.append(parse_one(fp))
        except Exception as e:
            errors.append(f"{fp.name}: {e}")

    df = pd.DataFrame(rows)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"JSON files: {len(files)}")
    print(f"Saved CSV: {OUTPUT_CSV}")
    print(f"Rows: {len(df)}")

    # Quick missing stats
    for col in ["year", "mileage_km", "price_usd", "body_type", "transmission", "plate_no"]:
        if col in df.columns:
            missing = df[col].isna().sum() if df[col].dtype != object else (df[col].fillna("").astype(str).str.strip() == "").sum()
            print(f"Missing {col}: {missing}")

    if errors:
        print("\nErrors (first 10):")
        for x in errors[:10]:
            print(" -", x)


if __name__ == "__main__":
    main()