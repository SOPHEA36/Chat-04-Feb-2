from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = PROJECT_ROOT / "vector_db" / "chroma_preowned"
COLLECTION = "preowned_listings"

embed_fn = SentenceTransformerEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=str(CHROMA_DIR))

try:
    client.delete_collection(COLLECTION)
    print("Deleted collection:", COLLECTION)
except Exception as e:
    print("Delete collection skipped:", e)

col = client.get_or_create_collection(COLLECTION, embedding_function=embed_fn)
print("Ready collection:", COLLECTION, "count:", col.count())