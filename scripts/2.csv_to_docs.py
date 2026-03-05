import csv
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv"
DOCS_DIR = PROJECT_ROOT / "data" / "docs"


def safe_filename(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-]+", "", text)
    return text[:80] if text else "unknown"


def clean_value(v):
    if v is None:
        return ""
    s = str(v).strip()
    return s


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit(f"No rows found in: {CSV_PATH}")

    created = 0

    for r in rows:
        brand = clean_value(r.get("brand"))
        model = clean_value(r.get("model"))
        price_usd = clean_value(r.get("price_usd"))
        seats = clean_value(r.get("seats"))
        body_type = clean_value(r.get("body_type"))
        fuel = clean_value(r.get("fuel"))
        url = clean_value(r.get("url"))

        title = f"{brand} {model}".strip()
        fname = f"{safe_filename(brand)}__{safe_filename(model)}.txt"
        out_path = DOCS_DIR / fname

        lines = []
        lines.append(f"Model: {title}")
        if price_usd:
            lines.append(f"Price (USD): {price_usd}")
        if body_type:
            lines.append(f"Body type: {body_type}")
        if seats:
            lines.append(f"Seating capacity: {seats}")
        if fuel:
            lines.append(f"Fuel: {fuel}")

        # Add key specs (all spec_* fields)
        spec_keys = sorted([k for k in r.keys() if k.startswith("spec_")])
        if spec_keys:
            lines.append("")
            lines.append("Specifications:")
            for k in spec_keys:
                v = clean_value(r.get(k))
                if not v:
                    continue
                label = k.replace("spec_", "").replace("_", " ").strip().title()
                lines.append(f"- {label}: {v}")

        if url:
            lines.append("")
            lines.append(f"Source: {url}")

        content = "\n".join(lines).strip() + "\n"
        out_path.write_text(content, encoding="utf-8")
        created += 1

    print(f"OK: created {created} docs in {DOCS_DIR}")


if __name__ == "__main__":
    main()