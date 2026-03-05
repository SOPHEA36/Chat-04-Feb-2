# scripts/preowned_rag_engine.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
import re
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s:
        return None
    s = re.sub(r"[^\d]+", "", s)
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, float):
        return v
    if isinstance(v, int):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(",", "")
    s = re.sub(r"[^\d\.]+", "", s)
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _safe_str(v: Any) -> str:
    if v in (None, "", "nan", "NaN"):
        return ""
    return str(v).strip()


def _extract_field_from_doc(doc: str, field_name: str) -> str:
    if not doc:
        return ""
    pattern = rf"^{re.escape(field_name)}\s*:\s*(.*)\s*$"
    for line in doc.splitlines():
        m = re.match(pattern, line.strip(), flags=re.IGNORECASE)
        if m:
            return (m.group(1) or "").strip()
    return ""


def _format_usd(v: Any) -> str:
    x = _to_float(v)
    if x is None:
        return "N/A"
    return f"${x:,.0f}"


class PreownedRAGEngine:
    available = False

    def __init__(
        self,
        chroma_dir: str,
        collection_name: str = "preowned_listings",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.chroma_dir = str(Path(chroma_dir).expanduser().resolve())
        self.collection_name = collection_name

        self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name=embedding_model)

        self.client = chromadb.PersistentClient(
            path=self.chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
        )

        self.available = True

    def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception:
            return 0

    def query(self, user_text: str, top_k: int = 5) -> Tuple[List[Dict[str, Any]], str]:
        user_text = (user_text or "").strip()
        if not user_text:
            return [], "Please type a question."

        res = self.collection.query(
            query_texts=[user_text],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        hits: List[Dict[str, Any]] = []
        for i in range(min(len(docs), len(metas), len(dists))):
            doc = docs[i] or ""
            meta = metas[i] or {}
            dist = dists[i]

            listing_id = _safe_str(meta.get("listing_id")) or _extract_field_from_doc(doc, "Listing ID")
            model = _safe_str(meta.get("model")) or _extract_field_from_doc(doc, "Model")
            year = _to_int(meta.get("year")) or _to_int(_extract_field_from_doc(doc, "Year"))
            price_usd = _to_float(meta.get("price_usd")) or _to_float(_extract_field_from_doc(doc, "Price (USD)"))
            mileage_km = _to_int(meta.get("mileage_km")) or _to_int(_extract_field_from_doc(doc, "Mileage (km)"))
            body_type = _safe_str(meta.get("body_type")) or _extract_field_from_doc(doc, "Body Type")
            body_color = _safe_str(meta.get("body_color")) or _extract_field_from_doc(doc, "Body Color")
            plate_no = _safe_str(meta.get("plate_no")) or _extract_field_from_doc(doc, "Plate No")

            source_url = (
                _safe_str(meta.get("source_url"))
                or _safe_str(meta.get("url"))
                or _safe_str(meta.get("source"))
            )
            if not source_url:
                source_url = _extract_field_from_doc(doc, "Source URL")

            hits.append(
                {
                    "listing_id": listing_id,
                    "model": model,
                    "year": year,
                    "price_usd": price_usd,
                    "mileage_km": mileage_km,
                    "body_type": body_type,
                    "body_color": body_color,
                    "plate_no": plate_no,
                    "source_url": source_url,
                    "distance": float(dist) if dist is not None else None,
                    "doc": doc,
                    "meta": meta,
                }
            )

        if not hits:
            return [], "No matching pre-owned listings found in the dataset."

        answer_text = self._build_listing_answer(hits)
        return hits, answer_text

    def rag_answer(self, user_text: str, last_model_norm: str | None = None) -> Dict[str, Any]:
        hits, answer_text = self.query(user_text, top_k=5)

        urls: List[str] = []
        for h in hits:
            u = (h.get("source_url") or "").strip()
            if u and u not in urls:
                urls.append(u)

        return {
            "answer_type": "preowned_rag",
            "text": answer_text,
            "facts": [answer_text] if answer_text else [],
            "sources": urls,
        }

    def _build_listing_answer(self, hits: List[Dict[str, Any]]) -> str:
        model_counts: Dict[str, int] = {}
        for h in hits:
            m = (h.get("model") or "").strip()
            if m:
                model_counts[m] = model_counts.get(m, 0) + 1

        top_model = ""
        if model_counts:
            top_model = sorted(model_counts.items(), key=lambda x: (-x[1], x[0]))[0][0]

        prices = [h.get("price_usd") for h in hits if h.get("price_usd") is not None]
        pmin = min(prices) if prices else None
        pmax = max(prices) if prices else None

        title = top_model if top_model else "Pre-owned listings"
        lines: List[str] = []
        lines.append(f"{title} — available pre-owned listings (top {len(hits)}):")

        for h in hits:
            price = _format_usd(h.get("price_usd"))
            year = h.get("year") if h.get("year") is not None else "N/A"
            mileage = h.get("mileage_km")
            mileage_txt = f"{mileage:,} km" if isinstance(mileage, int) else "N/A"
            plate = _safe_str(h.get("plate_no")) or "N/A"
            color = _safe_str(h.get("body_color")) or "N/A"
            body_type = _safe_str(h.get("body_type")) or "N/A"
            lines.append(f"- {price} | {year} | {mileage_txt} | {plate} | {color} | {body_type}")

        if pmin is not None and pmax is not None:
            lines.append(f"Price range: {_format_usd(pmin)} – {_format_usd(pmax)} ({len(hits)} listing(s))")

        return "\n".join(lines).strip()