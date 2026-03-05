# import chromadb
# from chromadb.config import Settings
# from pathlib import Path
#
# PROJECT_ROOT = Path(__file__).resolve().parent
# DB_DIR = PROJECT_ROOT / "vector_db" / "chroma"
#
# client = chromadb.PersistentClient(
#     path=str(DB_DIR),
#     settings=Settings(anonymized_telemetry=False),
# )
#
# collection = client.get_or_create_collection("vehicle_specs")
#
# print("Total chunks in DB:", collection.count())
#
# peek = collection.peek(limit=3)
#
# print("\nSample IDs:")
# print(peek.get("ids"))
#
# print("\nSample metadata:")
# print(peek.get("metadatas"))
#
# print("\nSample text:")
# for d in peek.get("documents", []):
#     print(d[:150])

import chromadb
from chromadb.config import Settings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
dbs = {
    "chroma": ROOT / "vector_db" / "chroma",
    "chroma_preowned": ROOT / "vector_db" / "chroma_preowned",
    "chroma_services": ROOT / "vector_db" / "chroma_services",
}

for name, path in dbs.items():
    print("\n====", name, "====")
    print("Path:", path)
    client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
    cols = client.list_collections()
    if not cols:
        print("No collections found.")
        continue
    for c in cols:
        col = client.get_collection(c.name)
        print(f"Collection: {c.name} | count={col.count()}")

