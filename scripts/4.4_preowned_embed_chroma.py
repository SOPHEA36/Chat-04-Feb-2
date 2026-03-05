import json
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHROMA_DIR = PROJECT_ROOT / "vector_db" / "chroma_preowned"
COLLECTION_NAME = "preowned_listings"

CHUNKS_JSONL = PROJECT_ROOT / "data_preowned" / "processed_preowned" / "preowned_chunks.jsonl"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    if not CHUNKS_JSONL.exists():
        raise FileNotFoundError(CHUNKS_JSONL)

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"domain": "toyota_preowned", "embedding_model": EMBED_MODEL},
    )

    rows = read_jsonl(CHUNKS_JSONL)

    ids = [r["id"] for r in rows]
    docs = [r["text"] for r in rows]
    metas = []
    for r in rows:
        metas.append({
            "source_file": r.get("source_file", ""),
            "chunk_index": int(r.get("chunk_index", 0)),
            "doc_type": r.get("doc_type", "preowned"),
        })

    batch_size = 256
    for i in range(0, len(rows), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            documents=docs[i:i+batch_size],
            metadatas=metas[i:i+batch_size],
        )
        print(f"Added {min(i+batch_size, len(rows))}/{len(rows)}")

    print("Done.")
    print("Collection:", COLLECTION_NAME)
    print("Count:", collection.count())
    print("Chroma dir:", CHROMA_DIR)


if __name__ == "__main__":
    main()