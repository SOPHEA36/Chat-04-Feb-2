# # scripts/services_rag_engine.py
# from __future__ import annotations
#
# import re
# import subprocess
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Any, Dict, List, Optional
#
# import chromadb
# from chromadb.utils import embedding_functions
#
#
# @dataclass
# class ServiceHit:
#     chunk_id: str
#     title: str
#     content: str
#     url: str
#     score: float
#
#
# class OllamaLLM:
#     def __init__(self, model: str = "llama3"):
#         self.model = model
#
#     def generate(self, prompt: str) -> str:
#         p = subprocess.run(
#             ["ollama", "run", self.model],
#             input=prompt.encode("utf-8"),
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             check=False,
#         )
#         return p.stdout.decode("utf-8", errors="ignore").strip()
#
#
# class ServicesRAGEngine:
#     available = True
#
#     def __init__(
#         self,
#         chroma_dir: Path,
#         collection_name: str = "services_pages",
#         llm_model: str = "llama3",
#         embed_model: str = "sentence-transformers/all-MiniLM-L6-v2",
#         top_k: int = 6,
#         min_score: float = 0.18,
#     ):
#         self.chroma_dir = Path(chroma_dir)
#         self.collection_name = collection_name
#         self.top_k = int(top_k)
#         self.min_score = float(min_score)
#
#         self._client = chromadb.PersistentClient(path=str(self.chroma_dir))
#
#         # Keep embedding function locally (NOT attached to collection)
#         self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
#             model_name=embed_model
#         )
#
#         # IMPORTANT: do NOT pass embedding_function here (prevents conflict)
#         self._col = self._client.get_or_create_collection(name=self.collection_name)
#
#         self._llm = OllamaLLM(model=llm_model)
#
#     def _retrieve(self, query: str, top_k: Optional[int] = None) -> List[ServiceHit]:
#         q = (query or "").strip()
#         if not q:
#             return []
#
#         k = int(top_k or self.top_k)
#
#         # Compute embeddings ourselves
#         q_emb = self._embed_fn([q])
#
#         res = self._col.query(
#             query_embeddings=q_emb,
#             n_results=k,
#             include=["documents", "metadatas", "distances"],
#         )
#
#         ids = (res.get("ids") or [[]])[0] or []
#         docs = (res.get("documents") or [[]])[0] or []
#         metas = (res.get("metadatas") or [[]])[0] or []
#         dists = (res.get("distances") or [[]])[0] or []
#
#         n = min(len(ids), len(docs), len(metas), len(dists))
#
#         hits: List[ServiceHit] = []
#         for i in range(n):
#             meta = metas[i] or {}
#             dist = float(dists[i]) if dists[i] is not None else 999.0
#             score = 1.0 / (1.0 + dist)
#
#             if score < self.min_score:
#                 continue
#
#             hits.append(
#                 ServiceHit(
#                     chunk_id=str(ids[i]),
#                     title=str(meta.get("title") or ""),
#                     content=str(docs[i] or ""),
#                     url=str(meta.get("url") or ""),   # services_index.py uses "url"
#                     score=score,
#                 )
#             )
#
#         hits.sort(key=lambda x: x.score, reverse=True)
#         return hits
#
#     def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
#         hits = self._retrieve(user_text)
#         if not hits:
#             msg = "I do not have e  nough information in the knowledge base to answer that."
#             return {"answer_type": "rag", "text": msg, "facts": [msg], "sources": []}
#
#         context = "\n\n---\n\n".join(
#             f"TITLE: {h.title}\nURL: {h.url}\nCONTENT:\n{h.content}"
#             for h in hits
#         )
#
#         prompt = (
#             "You are a Toyota Cambodia assistant.\n"
#             "Use only the CONTEXT.\n"
#             "If missing, say you do not have enough information in the knowledge base.\n\n"
#             f"QUESTION:\n{user_text}\n\n"
#             f"CONTEXT:\n{context}\n"
#         )
#
#         ans = self._llm.generate(prompt)
#
#         sources: List[str] = []
#         for h in hits:
#             if h.url and h.url not in sources:
#                 sources.append(h.url)
#
#         return {"answer_type": "rag", "text": ans, "facts": [ans], "sources": sources}
#
# 5th-March-26

# scripts/services_rag_engine.py
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import chromadb
from chromadb.config import Settings


@dataclass
class ServiceHit:
    chunk_id: str
    domain: str
    title: str
    content: str
    source_url: str
    source_id: str
    score: float


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _score_from_distance(dist: Optional[float]) -> float:
    if dist is None:
        return 0.0
    try:
        d = float(dist)
    except Exception:
        return 0.0
    return 1.0 / (1.0 + d)


def _low(s: Any) -> str:
    return (str(s) or "").strip().lower()


def _clip(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3].rstrip() + "..."


class ServicesRAGEngine:
    def __init__(
        self,
        chroma_dir: Path,
        collection_name: str = "services_pages",
        llm_model: str = "llama3",
        ollama_url: str = "http://localhost:11434/api/generate",
        top_k: int = 8,
        min_score: float = 0.12,
        max_context_chars_per_hit: int = 900,
        max_hits_in_context: int = 5,
        ollama_timeout: int = 90,
        ollama_keep_alive: str = "10m",
    ):
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.llm_model = llm_model
        self.ollama_url = ollama_url

        self.top_k = int(top_k)
        self.min_score = float(min_score)

        self.max_context_chars_per_hit = int(max_context_chars_per_hit)
        self.max_hits_in_context = int(max_hits_in_context)

        self.ollama_timeout = int(ollama_timeout)
        self.ollama_keep_alive = str(ollama_keep_alive)

        self._client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )

        # Avoid embedding_function conflict: do not pass embedding_function here.
        try:
            self._col = self._client.get_collection(name=self.collection_name)
        except Exception:
            self._col = self._client.get_or_create_collection(name=self.collection_name)

    # ----------------------------
    # Topic routing / source boost
    # ----------------------------
    def _classify(self, user_text: str) -> str:
        t = _low(user_text)

        if re.search(r"\b(service\s*[a-d]\b|service\s+package|servicing\s+package|service\s+packages|coupon|coupons|34\s*point|41\s*point|46\s*point|53\s*point|5000\s*km|10000\s*km|20000\s*km|40000\s*km)\b", t):
            return "packages"

        if re.search(r"\b(warranty|oem|genuine\s+parts|coverage|covered|guarantee)\b", t):
            return "warranty"

        if re.search(r"\b(maintenance|maintain|repair|periodic|schedule|interval|service\s+interval)\b", t):
            return "maintenance"

        if re.search(r"\b(contact|hotline|phone|address|location|showroom|dealer|workshop|service\s+center|service\s+centre|branch)\b", t):
            return "contact"

        if re.search(r"\b(about|company|profile|history|mission|vision|distributor)\b", t):
            return "about"

        return "general"

    def _preferred_sources(self, topic: str) -> List[str]:
        # these are the JSON/TXT stems used in services_index.py:
        # about-toyota-cambodia, maintenance-and-repair, oem-warranty, servicing-packages
        if topic == "packages":
            return ["servicing-packages"]
        if topic == "warranty":
            return ["oem-warranty"]
        if topic == "maintenance":
            return ["maintenance-and-repair", "servicing-packages"]
        if topic == "about":
            return ["about-toyota-cambodia"]
        if topic == "contact":
            # contact info may appear on about/maintenance pages depending on your scrape
            return ["about-toyota-cambodia", "maintenance-and-repair"]
        return ["servicing-packages", "oem-warranty", "maintenance-and-repair", "about-toyota-cambodia"]

    def _boost(self, hit: ServiceHit, topic: str, preferred: List[str], query: str) -> float:
        # base score from vector distance
        s = hit.score

        sid = _low(hit.source_id)
        if any(sid.startswith(p) for p in preferred):
            s += 0.25

        # light keyword boost
        q = _low(query)
        c = _low(hit.content)
        if topic == "packages":
            keys = ["service a", "service b", "service c", "service d", "point check", "coupon", "km", "months", "usd", "price"]
        elif topic == "warranty":
            keys = ["warranty", "coverage", "covered", "genuine parts", "oem", "period", "terms", "conditions"]
        elif topic == "maintenance":
            keys = ["maintenance", "periodic", "schedule", "interval", "inspection", "repair"]
        else:
            keys = ["toyota", "cambodia", "service", "warranty", "maintenance"]

        hit_count = 0
        for k in keys:
            if k in q and k in c:
                hit_count += 1
        if hit_count:
            s += min(0.18, 0.06 * hit_count)

        return s

    # ----------------------------
    # Retrieval
    # ----------------------------
    def _retrieve(self, query: str, top_k: Optional[int] = None) -> List[ServiceHit]:
        q = (query or "").strip()
        if not q:
            return []

        k = int(top_k or self.top_k)

        where: Optional[Dict[str, Any]] = None
        # If your metadata includes domain="services" (it does), restrict to services domain.
        where = {"domain": "services"}

        res = self._col.query(
            query_texts=[q],
            where=where,
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        ids = (res.get("ids") or [[]])[0] or []
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        dists = (res.get("distances") or [[]])[0] or []

        n = min(len(ids), len(docs), len(metas), len(dists))
        hits: List[ServiceHit] = []

        for i in range(n):
            meta = metas[i] or {}
            score = _score_from_distance(dists[i])

            if score < self.min_score:
                continue

            hits.append(
                ServiceHit(
                    chunk_id=str(ids[i]),
                    domain=str(meta.get("domain", "services")),
                    title=str(meta.get("title", "")),
                    content=str(docs[i] or ""),
                    source_url=str(meta.get("url", "")),
                    source_id=str(meta.get("source", "")),
                    score=score,
                )
            )

        if not hits:
            return []

        topic = self._classify(q)
        preferred = self._preferred_sources(topic)

        # rerank with boosting
        boosted: List[Tuple[float, ServiceHit]] = []
        for h in hits:
            boosted.append((self._boost(h, topic, preferred, q), h))

        boosted.sort(key=lambda x: x[0], reverse=True)

        # keep only top hits for context (faster)
        final_hits = [x[1] for x in boosted[: max(3, self.max_hits_in_context)]]
        return final_hits

    # ----------------------------
    # Prompt + LLM
    # ----------------------------
    def _build_prompt(self, user_text: str, hits: List[ServiceHit]) -> str:
        topic = self._classify(user_text)

        blocks: List[str] = []
        for h in hits[: self.max_hits_in_context]:
            blocks.append(
                "SOURCE_URL: {url}\nTITLE: {title}\nCONTENT:\n{content}".format(
                    url=h.source_url,
                    title=h.title,
                    content=_clip(_normalize_ws(h.content), self.max_context_chars_per_hit),
                )
            )
        context = "\n\n---\n\n".join(blocks)

        extra = ""
        if topic == "packages":
            extra = (
                "If the question is about Service A/B/C/D, answer using the Servicing Packages content only.\n"
                "If prices or inclusions are present, list them clearly.\n"
            )
        elif topic == "warranty":
            extra = (
                "If the question is about OEM warranty, summarize what is covered and any clear conditions found.\n"
            )
        elif topic == "maintenance":
            extra = (
                "If the question is about maintenance schedule/interval, summarize the schedule mentioned in context.\n"
            )

        return (
            "You are a Toyota Cambodia assistant.\n"
            "Rules:\n"
            "1) Answer only using the provided context.\n"
            "2) If the context is insufficient, say exactly: I do not have enough information in the knowledge base to answer that.\n"
            "3) Do not invent facts.\n"
            "4) Plain text only.\n"
            "5) Do not add any extra links not present in context.\n"
            f"{extra}\n"
            "USER QUESTION:\n"
            f"{user_text}\n\n"
            "CONTEXT:\n"
            f"{context}\n"
        )

    def _ollama_generate(self, prompt: str) -> str:
        try:
            r = requests.post(
                self.ollama_url,
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": self.ollama_keep_alive,
                },
                timeout=self.ollama_timeout,
            )
            data = r.json()
            return str(data.get("response", "")).strip()
        except Exception:
            return ""

    @staticmethod
    def _unique_sources(hits: List[ServiceHit], max_n: int = 3) -> List[str]:
        out: List[str] = []
        for h in hits:
            u = (h.source_url or "").strip()
            if u and u not in out:
                out.append(u)
            if len(out) >= max_n:
                break
        return out

    def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
        hits = self._retrieve(user_text, top_k=self.top_k)

        if not hits:
            msg = "I do not have enough information in the knowledge base to answer that."
            return {
                "answer_type": "rag",
                "text": msg,
                "facts": [msg],
                "sources": [],
                "evidence": [],
            }

        prompt = self._build_prompt(user_text, hits)
        ans = self._ollama_generate(prompt).strip()

        if not ans:
            ans = "I do not have enough information in the knowledge base to answer that."

        sources = self._unique_sources(hits, max_n=3)
        evidence = [
            {
                "chunk_id": h.chunk_id,
                "score": round(h.score, 4),
                "source_url": h.source_url,
                "source": h.source_id,
            }
            for h in hits
        ]

        return {
            "answer_type": "rag",
            "text": ans,
            "facts": [ans],
            "sources": sources,
            "evidence": evidence,
        }




