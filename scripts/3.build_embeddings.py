import argparse
import csv
import re
import shutil
from pathlib import Path
from typing import Dict, Tuple, Optional, List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "data" / "docs"
CSV_MIN = PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv"
DB_DIR = PROJECT_ROOT / "vector_db" / "chroma"
COLLECTION_NAME = "vehicle_specs"

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def to_int_safe(v) -> Optional[int]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s))
    except Exception:
        return None


def load_metadata_index(csv_path: Path) -> Dict[Tuple[str, str], dict]:
    index: Dict[Tuple[str, str], dict] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            brand = norm_text(r.get("brand"))
            model = norm_text(r.get("model"))

            meta = {
                "brand": r.get("brand") or "",
                "model": r.get("model") or "",
                "price_usd": to_int_safe(r.get("price_usd")),
                "seats": to_int_safe(r.get("seats")),
                "body_type": r.get("body_type") or "",
                "fuel": r.get("fuel") or "",
                "url": r.get("url") or "",
                "source_file": r.get("source_file") or "",
            }
            index[(brand, model)] = meta
    return index


def parse_model_line(doc_text: str) -> Tuple[str, str]:
    """
    Expects first line like: "Model: Toyota Corolla Cross HEV"
    Returns (brand_guess, model_guess)
    """
    lines = [ln.strip() for ln in doc_text.splitlines() if ln.strip()]
    if not lines:
        return "", ""

    first = lines[0]
    if first.lower().startswith("model:"):
        value = first.split(":", 1)[1].strip()
    else:
        value = first.strip()

    parts = value.split()
    if len(parts) < 2:
        return value, ""

    brand_guess = parts[0]
    model_guess = " ".join(parts[1:])
    return brand_guess, model_guess


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)

    return chunks


def reset_db(db_dir: Path):
    if db_dir.exists():
        shutil.rmtree(db_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if args.reset:
        reset_db(DB_DIR)

    if not DOCS_DIR.exists():
        raise SystemExit(f"Docs folder not found: {DOCS_DIR}")
    if not CSV_MIN.exists():
        raise SystemExit(f"CSV not found: {CSV_MIN}")

    metadata_index = load_metadata_index(CSV_MIN)
    doc_files = sorted(DOCS_DIR.glob("*.txt"))
    if not doc_files:
        raise SystemExit(f"No .txt docs found in: {DOCS_DIR}")

    client = chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    embedder = SentenceTransformer(args.model)

    all_ids = []
    all_docs = []
    all_metas = []

    for fp in doc_files:
        text = fp.read_text(encoding="utf-8", errors="ignore")
        brand_guess, model_guess = parse_model_line(text)

        key = (norm_text(brand_guess), norm_text(model_guess))
        meta_base = metadata_index.get(key)

        # Fallback if mismatch: try matching by filename (brand__model format)
        if meta_base is None:
            name = fp.stem
            if "__" in name:
                fb_brand, fb_model = name.split("__", 1)
                key2 = (norm_text(fb_brand), norm_text(fb_model.replace("-", " ")))
                meta_base = metadata_index.get(key2)

        if meta_base is None:
            meta_base = {
                "brand": brand_guess,
                "model": model_guess,
                "price_usd": None,
                "seats": None,
                "body_type": "",
                "fuel": "",
                "url": "",
                "source_file": fp.name,
            }

        chunks = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)
        for i, chunk in enumerate(chunks):
            doc_id = f"{fp.stem}::{i}"
            meta = dict(meta_base)
            meta["doc_file"] = fp.name
            meta["chunk_index"] = i
            meta["chunk_count"] = len(chunks)

            all_ids.append(doc_id)
            all_docs.append(chunk)
            all_metas.append(meta)

    # Embed in batches (SentenceTransformer handles batching internally)
    embeddings = embedder.encode(all_docs, show_progress_bar=True, normalize_embeddings=True)

    # Upsert into Chroma
    collection.upsert(
        ids=all_ids,
        documents=all_docs,
        metadatas=all_metas,
        embeddings=embeddings.tolist()
    )

    print(f"OK: indexed {len(doc_files)} documents")
    print(f"OK: stored {len(all_ids)} chunks in Chroma")
    print(f"DB_DIR: {DB_DIR}")
    print(f"Collection: {COLLECTION_NAME}")


if __name__ == "__main__":
    main()