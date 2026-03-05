from pathlib import Path
import re
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CSV_PATH = PROJECT_ROOT / "data_preowned" / "csv_preowned" / "preowned_master.csv"
DOCS_DIR = PROJECT_ROOT / "data_preowned" / "docs_preowned"


def clean_text(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    s = re.sub(r"\s+", " ", s)
    return s


def safe_name(s: str) -> str:
    s = clean_text(s).replace("/", "-")
    s = re.sub(r"[^A-Za-z0-9\-_ ]+", "-", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s or "unknown"


def build_doc(row: dict) -> str:
    lines = ["Toyota Certified Pre-Owned Listing"]

    def add(label: str, key: str):
        val = clean_text(row.get(key, ""))
        if val != "":
            lines.append(f"{label}: {val}")

    add("Listing ID", "listing_id")
    add("Brand", "brand")
    add("Model", "model")
    add("Year", "year")
    add("Price (USD)", "price_usd")
    add("Mileage (km)", "mileage_km")
    add("Body Type", "body_type")
    add("Body Color", "body_color")
    add("Engine", "engine")
    add("Fuel", "fuel")
    add("Transmission", "transmission")
    add("Plate No", "plate_no")
    add("Source URL", "source_url")

    return "\n".join(lines) + "\n"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for _, r in df.iterrows():
        row = r.to_dict()

        listing_id = safe_name(row.get("listing_id", ""))
        model = safe_name(row.get("model", ""))
        plate = safe_name(row.get("plate_no", ""))

        out_name = f"preowned__{model}__{plate}__{listing_id}.txt"
        out_path = DOCS_DIR / out_name
        out_path.write_text(build_doc(row), encoding="utf-8")
        count += 1

    print(f"Saved {count} docs to: {DOCS_DIR}")


if __name__ == "__main__":
    main()