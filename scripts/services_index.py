# scripts/services_index.py
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DOCS_DIR = PROJECT_ROOT / "data_services" / "docs_services"
SERVICES_JSON_DIR = PROJECT_ROOT / "data_services" / "json_services"

DB_DIR = PROJECT_ROOT / "vector_db" / "chroma_services"
COLLECTION_NAME = "services_pages"

def connect():
    client = chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(COLLECTION_NAME)

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def chunk_paragraphs(text: str, max_chars: int = 900) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in parts:
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            if len(p) <= max_chars:
                buf = p
            else:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars].strip())
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks

def load_from_txt() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not SERVICES_DOCS_DIR.exists():
        return out
    for p in sorted(SERVICES_DOCS_DIR.glob("*.txt")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        out.append(
            {
                "id": p.stem,
                "title": p.stem.replace("-", " ").title(),
                "url": "",
                "text": text,
            }
        )
    return out

def load_from_json() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not SERVICES_JSON_DIR.exists():
        return out
    for p in sorted(SERVICES_JSON_DIR.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        url = data.get("url") or ""
        title = data.get("page_title") or data.get("title") or p.stem
        raw = data.get("raw_text") or ""
        if not raw:
            raw = json.dumps(data.get("content") or {}, ensure_ascii=False, indent=2)
        out.append(
            {
                "id": p.stem,
                "title": str(title),
                "url": str(url),
                "text": str(raw),
            }
        )
    return out

def main():
    col = connect()

    items = load_from_json()
    if not items:
        items = load_from_txt()

    if not items:
        print("No services docs found.")
        return

    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    for it in items:
        chunks = chunk_paragraphs(it["text"])
        for idx, ch in enumerate(chunks, start=1):
            doc_id = f"{it['id']}::{idx:03d}"
            ids.append(doc_id)
            docs.append(normalize_ws(ch))
            metas.append(
                {
                    "source": it["id"],
                    "title": it["title"],
                    "url": it.get("url") or "",
                    "source_url": it.get("url") or "",
                    "domain": "services",
                }
            )

    if ids:
        col.upsert(ids=ids, documents=docs, metadatas=metas)

    print(f"Indexed services: {len(items)} files, {len(ids)} chunks")
    print(f"DB: {DB_DIR}")
    print(f"Collection: {COLLECTION_NAME}")

if __name__ == "__main__":
    main()