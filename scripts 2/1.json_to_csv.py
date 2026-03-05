import json
import re
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = PROJECT_ROOT / "data" / "json"
CSV_DIR = PROJECT_ROOT / "data" / "csv"

OUT_MASTER = CSV_DIR / "vehicle_master.csv"
OUT_MIN = CSV_DIR / "vehicle_master_min.csv"


def parse_price_to_number(price_value):
    """
    Convert "$47,900" or "47,900" or 47900 -> 47900 (int).
    Returns None if cannot parse.
    """
    if price_value is None:
        return None

    if isinstance(price_value, (int, float)):
        return int(price_value)

    text = str(price_value).strip()
    # keep digits only
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    return int(digits)


def normalize_key(key: str) -> str:
    key = key.strip()
    key = key.replace("/", "_")
    key = re.sub(r"\s+", "_", key)
    key = re.sub(r"[^A-Za-z0-9_]+", "", key)
    return key.lower()


def detect_fuel(model_name: str, specs: dict) -> str:
    """
    Best-effort fuel detection from model name and Engine type/spec fields.
    Returns one of: gasoline, diesel, hybrid, ev, unknown
    """
    text_parts = [str(model_name or "")]
    if isinstance(specs, dict):
        engine_type = specs.get("Engine type") or specs.get("Engine Type") or ""
        text_parts.append(str(engine_type))
    text = " ".join(text_parts).lower()

    if "hev" in text or "hybrid" in text:
        return "hybrid"
    if "diesel" in text:
        return "diesel"
    if "electric" in text or "bev" in text or "ev" in text:
        return "ev"
    if "gasoline" in text or "petrol" in text or "gas" in text:
        return "gasoline"
    return "unknown"


def main():
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    json_files = sorted(JSON_DIR.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No JSON files found in: {JSON_DIR}")

    rows = []
    all_fields = set()

    for fp in json_files:
        with fp.open("r", encoding="utf-8") as f:
            data = json.load(f)

        brand = data.get("brand")
        model = data.get("model")
        url = data.get("url")
        price_raw = data.get("price")
        price_usd = parse_price_to_number(price_raw)

        specs = data.get("specifications") or {}
        if not isinstance(specs, dict):
            specs = {}

        # Try common fields
        seating = specs.get("Seating capacity") or specs.get("seating capacity")
        seats = None
        try:
            seats = int(str(seating).strip()) if seating is not None and str(seating).strip() != "" else None
        except ValueError:
            seats = None

        body_type = specs.get("Body_type") or specs.get("Body Type") or specs.get("body_type") or specs.get("Body Type ")
        fuel = detect_fuel(model, specs)

        row = {
            "source_file": fp.name,
            "brand": brand,
            "model": model,
            "price_raw": price_raw,
            "price_usd": price_usd,
            "url": url,
            "seats": seats,
            "body_type": body_type,
            "fuel": fuel,
        }

        # Flatten all specs into columns like spec_engine_type, spec_transmission_type, ...
        for k, v in specs.items():
            col = "spec_" + normalize_key(str(k))
            row[col] = v

        rows.append(row)
        all_fields.update(row.keys())

    # Stable field order: core fields first, then spec_* fields alphabetically
    core = ["source_file", "brand", "model", "price_raw", "price_usd", "seats", "body_type", "fuel", "url"]
    spec_fields = sorted([f for f in all_fields if f.startswith("spec_")])
    fieldnames = core + [f for f in spec_fields if f not in core]

    # Write master wide CSV
    with OUT_MASTER.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Write minimal CSV (for filtering/ranking)
    min_fields = ["brand", "model", "price_usd", "seats", "body_type", "fuel", "url", "source_file"]
    with OUT_MIN.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=min_fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in min_fields})

    print(f"OK: {len(rows)} JSON files processed")
    print(f"Saved: {OUT_MASTER}")
    print(f"Saved: {OUT_MIN}")


if __name__ == "__main__":
    main()