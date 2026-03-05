from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = PROJECT_ROOT / "vector_db" / "chroma_preowned"
COLLECTION = "preowned_listings"

embed_fn = SentenceTransformerEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
col = client.get_collection(COLLECTION, embedding_function=embed_fn)

tests = [
    "Fortuner Legender preowned price year mileage",
    "Veloz preowned price",
    "Corolla Cross Hybrid preowned year mileage",
    "Yaris Cross preowned",
]

for q in tests:
    print("\n" + "=" * 80)
    print("QUERY:", q)
    res = col.query(
        query_texts=[q],
        n_results=5,
        include=["documents", "metadatas", "distances"],
    )

    ids = res["ids"][0]
    dists = res["distances"][0]
    metas = res["metadatas"][0]
    docs = res["documents"][0]

    for i in range(len(ids)):
        print(f"\n#{i+1} id={ids[i]} dist={dists[i]}")
        print("meta:", metas[i])
        print("doc:", (docs[i] or "")[:260])