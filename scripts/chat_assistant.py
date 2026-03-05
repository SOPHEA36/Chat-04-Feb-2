# # # # scripts/chat_assistant.py
#
# from __future__ import annotations
#
# import os
# import re
# import subprocess
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Any, Dict, List, Optional
#
# _SCRIPTS_DIR = Path(__file__).resolve().parent
# _PROJECT_ROOT = _SCRIPTS_DIR.parent
#
# from scripts.response_style import style_answer, DEFAULT_STYLE
#
# # 1: CSV / Recommendation engine functions
# from scripts.csv_engine import (
#     detect_feature_key,
#     detect_model_in_text,
#     detect_models_in_text,
#     resolve_target_model,
#     answer_feature_from_csv,
#     answer_price_from_csv,
#     answer_specs_from_csv,
#     answer_summary_from_csv,
#     is_recommendation_intent,
#     is_spec_intent,
#     is_summary_intent,
#     extract_budget,
#     extract_seats,
#     extract_fuel,
#     extract_body_type,
#     filter_cars_split,
#     build_reco_answer,
#     find_row_by_model,
#     format_price_usd,
# )
#
# # 2: Pre-owned engine
# from scripts.preowned_engine import PreownedEngine, is_preowned_intent
#
#
# # =========================
# # 3: Real RAG (Chroma + LLM)
# # =========================
#
# @dataclass
# class RagHit:
#     chunk_id: str
#     title: str
#     content: str
#     source_url: str
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
#         out = p.stdout.decode("utf-8", errors="ignore").strip()
#         return out
#
#
# class ChromaRAGEngine:
#     """
#     Real RAG:
#     - retrieve chunks from Chroma
#     - send context to LLM
#     - return answer + sources + evidence
#     """
#     available = True
#
#     def __init__(
#         self,
#         chroma_dir: Path,
#         collection_name: str,
#         llm_model: str = "llama3",
#         embed_model: str = "sentence-transformers/all-MiniLM-L6-v2",
#         top_k: int = 5,
#         min_score: float = 0.18,
#     ):
#         try:
#             import chromadb
#             from chromadb.utils import embedding_functions
#         except Exception as e:
#             self.available = False
#             self._init_error = str(e)
#             return
#
#         self.chroma_dir = Path(chroma_dir)
#         self.collection_name = collection_name
#         self.top_k = int(top_k)
#         self.min_score = float(min_score)
#
#         self._client = chromadb.PersistentClient(path=str(self.chroma_dir))
#         self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
#             model_name=embed_model
#         )
#         self._col = self._client.get_or_create_collection(
#             name=self.collection_name,
#             embedding_function=self._embed_fn,
#         )
#
#         self._llm = OllamaLLM(model=llm_model)
#
#     def _retrieve(self, query: str, where=None, top_k: int = 6):
#         query = (query or "").strip()
#         if not query:
#             return []
#
#         res = self._col.query(
#             query_texts=[query],
#             where=where,
#             n_results=top_k,
#             include=["documents", "metadatas", "distances"],
#         )
#
#         ids = res.get("ids", [[]])[0] or []
#         docs = res.get("documents", [[]])[0] or []
#         metas = res.get("metadatas", [[]])[0] or []
#         dists = res.get("distances", [[]])[0] or []
#
#         n = min(len(docs), len(metas), len(dists), len(ids))
#
#         hits: List[RagHit] = []
#         for i in range(n):
#             meta = metas[i] or {}
#
#             dist_val = dists[i]
#             dist = float(dist_val) if dist_val is not None else 999.0
#             score = 1.0 / (1.0 + dist)
#
#             if score < self.min_score:
#                 continue
#
#             hits.append(
#                 RagHit(
#                     chunk_id=str(ids[i]),
#                     title=str(meta.get("title", "")),
#                     content=str(docs[i] or ""),
#                     source_url=str(meta.get("source_url", "")),
#                     score=score,
#                 )
#             )
#
#         hits.sort(key=lambda x: x.score, reverse=True)
#         return hits
#
#     @staticmethod
#     def _build_prompt(user_text: str, hits: List[RagHit]) -> str:
#         context_blocks: List[str] = []
#         for h in hits:
#             context_blocks.append(
#                 "SOURCE_URL: {url}\nTITLE: {title}\nCONTENT:\n{content}".format(
#                     url=h.source_url,
#                     title=h.title,
#                     content=h.content,
#                 )
#             )
#
#         context = "\n\n---\n\n".join(context_blocks)
#
#         return (
#             "You are a Toyota Cambodia assistant.\n"
#             "Rules:\n"
#             "1) Answer only using the provided context.\n"
#             "2) If context is insufficient, say you do not have enough information in the knowledge base.\n"
#             "3) Do not invent facts.\n"
#             "4) Write in plain text (no markdown bold, no icons).\n"
#             "5) End with a single line: Sources: <comma separated urls used>\n\n"
#             "USER QUESTION:\n"
#             f"{user_text}\n\n"
#             "CONTEXT:\n"
#             f"{context}\n"
#         )
#
#     @staticmethod
#     def _extract_sources_from_hits(hits: List[RagHit]) -> List[str]:
#         out: List[str] = []
#         for h in hits:
#             if h.source_url and h.source_url not in out:
#                 out.append(h.source_url)
#         return out
#
#     def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
#         hits = self._retrieve(user_text, where=None)
#         if not hits:
#             msg = "I do not have enough information in the knowledge base to answer that."
#             return {
#                 "answer_type": "rag",
#                 "text": msg,
#                 "facts": [msg],
#                 "sources": [],
#                 "evidence": [],
#             }
#
#         prompt = self._build_prompt(user_text, hits)
#         llm_text = self._llm.generate(prompt)
#
#         sources = self._extract_sources_from_hits(hits)
#         evidence = [{"chunk_id": h.chunk_id, "score": round(h.score, 4), "source_url": h.source_url} for h in hits]
#
#         return {
#             "answer_type": "rag",
#             "text": llm_text,
#             "facts": [llm_text],
#             "sources": sources,
#             "evidence": evidence,
#         }
#
#
# # 3b: Keep a safe fallback (no fixed answers anymore)
# class NoRAG:
#     available = False
#
#     def __init__(self, rows: List[Dict[str, Any]]):
#         self.rows = rows
#
#     def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
#         msg = (
#             "RAG is not available. Please ask about price, specs, features, comparisons, recommendations, or pre-owned listings."
#         )
#         return {"answer_type": "rag", "text": msg, "facts": [msg], "sources": []}
#
# def build_rag_engine(rows: List[Dict[str, Any]]):
#     import os
#     from scripts.rag_engine import VehicleRAGEngine
#     from scripts.services_rag_engine import ServicesRAGEngine
#
#     llm_model = os.environ.get("RAG_LLM_MODEL") or "llama3"
#
#     vehicle = VehicleRAGEngine(
#         rows,
#         llm_model=llm_model,
#         ollama_url=os.environ.get("OLLAMA_URL") or "http://localhost:11434/api/generate",
#     )
#
#     services = ServicesRAGEngine(
#         chroma_dir=_PROJECT_ROOT / "vector_db" / "chroma_services",
#         collection_name="services_pages",
#         llm_model=llm_model,
#         ollama_url=os.environ.get("OLLAMA_URL") or "http://localhost:11434/api/generate",
#     )
#
#     class Composite:
#         available = True
#
#         def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
#             if _is_warranty_or_services_info_question(user_text) or _is_service_company_rag_intent(user_text):
#                 return services.rag_answer(user_text, last_model_norm=last_model_norm)
#             return vehicle.rag_answer(user_text, last_model_norm=last_model_norm)
#
#     return Composite()
# def build_preowned_engine(preowned_csv_path: Optional[str] = None) -> PreownedEngine:
#     return PreownedEngine(csv_path=preowned_csv_path)
#
#
# # =========================
# # 4: Helpers
# # =========================
#
# def _low(s: Any) -> str:
#     return (str(s) or "").strip().lower()
#
#
# def _clean(text: str) -> str:
#     t = (text or "").strip()
#     t = re.sub(r"^\s*\d+[\.\)]\s*", "", t)  # remove "1) " prefix
#     t = t.strip('"\'`\u201c\u201d\u2018\u2019')
#     t = re.sub(r"\s+", " ", t).strip()
#     return t
#
#
# def _remove_markdown_bold(text: str) -> str:
#     if not text:
#         return text
#     return text.replace("**", "")
#
#
# def _pipe(res: Dict[str, Any], pipeline: str) -> Dict[str, Any]:
#     out = dict(res)
#     out["pipeline"] = pipeline
#     if "text" not in out:
#         out["text"] = out.get("answer") or ""
#     if "answer" not in out:
#         out["answer"] = out.get("text") or ""
#     out["text"] = _remove_markdown_bold(str(out.get("text") or ""))
#     out["answer"] = _remove_markdown_bold(str(out.get("answer") or ""))
#     return out
#
#
# def _sys(text: str) -> Dict[str, Any]:
#     text = _remove_markdown_bold(text)
#     return _pipe({"answer_type": "system", "text": text, "facts": [text], "sources": []}, "SYSTEM")
#
#
# def _csv_msg(text: str, answer_type: str = "system") -> Dict[str, Any]:
#     text = _remove_markdown_bold(text)
#     return _pipe({"answer_type": answer_type, "text": text, "facts": [text], "sources": []}, "CSV_METHOD")
#
#
# def _unknown_question_response(user_text: str, state: Dict[str, Any]) -> Dict[str, Any]:
#     t = (user_text or "").lower()
#     last_model = state.get("last_model")
#
#     # If user is asking about service / warranty / company topics, DO NOT talk about last_model.
#     if (
#         re.search(r"\b(warranty|guarantee|coverage|covered)\b", t)
#         or re.search(r"\b(service|services|servicing|maintenance|repair|package|packages|schedule|workshop|showroom|branch|dealer|contact|hotline)\b", t)
#         or re.search(r"\b(certified\s+pre.?owned|cpo)\b", t)
#     ):
#         hint = (
#             "Please ask a Toyota Cambodia question like:\n"
#             "- What service packages do you provide?\n"
#             "- Where is the service center / showroom?\n"
#             "- What is included in Toyota warranty?\n"
#             "- Toyota Certified Pre-Owned program details"
#         )
#         return _sys(hint)
#
#     if last_model:
#         hint = (
#             f"I'm not sure what you mean, but I was last discussing the {last_model}. "
#             f"You can ask me about its price, specs, features, or compare it with another model."
#         )
#         return _sys(hint)
#
#     if any(k in t for k in ["toyota", "car", "vehicle", "model"]):
#         hint = (
#             "I can help you with Toyota Cambodia vehicles. Try asking:\n"
#             "- Price of Fortuner / specs of Yaris Cross\n"
#             "- Compare Raize vs Veloz\n"
#             "- Recommend a car under $40,000\n"
#             "- Show pre-owned SUV under $35,000"
#         )
#         return _sys(hint)
#
#     hint = (
#         "I'm a Toyota Cambodia assistant. I can help with:\n"
#         "- Price and Specs\n"
#         "- Features\n"
#         "- Compare\n"
#         "- Recommend\n"
#         "- Pre-owned listings\n"
#         "- Service & Warranty"
#     )
#     return _sys(hint)
#
#
# def _reset_state(state: Dict[str, Any]) -> None:
#     state.clear()
#     state.update(
#         {
#             "last_model": None,
#             "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
#             "slot_fill_active": False,
#             "conversation_history": [],
#         }
#     )
#
#
# def _resolve_with_history(user_text: str, state: Dict[str, Any], full_rows) -> str:
#     t = user_text.lower().strip()
#     last_model = state.get("last_model")
#     has_pronoun = bool(re.search(r"\b(it|its|that|this|the car|the model|the vehicle)\b", t))
#     has_model = bool(detect_model_in_text(user_text, full_rows))
#
#     if has_pronoun and not has_model and last_model:
#         user_text = re.sub(r"\b(it|its)\b", last_model, user_text, flags=re.IGNORECASE)
#
#     return user_text
#
#
# def _cancel_reco_flow(state: Dict[str, Any]) -> None:
#     state["slot_fill_active"] = False
#     state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
#
#
# def _missing_slots(slots: Dict[str, Any]) -> List[str]:
#     missing: List[str] = []
#     if slots.get("max_budget") is None:
#         missing.append("budget")
#     if not slots.get("body_type"):
#         missing.append("body")
#     if not slots.get("fuel"):
#         missing.append("fuel")
#     return missing
#
#
# # 4.5: Model index + unknown model detection (NO hardcoded model names)
# def _norm_model_name(s: str) -> str:
#     x = (s or "").strip().lower()
#     x = re.sub(r"[^a-z0-9]+", " ", x)
#     x = re.sub(r"\s+", " ", x).strip()
#     return x
#
#
# def _known_model_norms(full_rows: List[Dict[str, Any]]) -> set:
#     out = set()
#     for r in full_rows:
#         m = str(r.get("model") or "").strip()
#         if m:
#             out.add(_norm_model_name(m))
#     return out
#
#
# def _extract_model_candidate(user_text: str) -> Optional[str]:
#     t = _low(user_text)
#
#     patterns = [
#         r"\bprice\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bhow\s+much\s+is\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bcost\s+of\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bstarting\s+price\s+(?:of|for)\s+([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bspecs?\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bspecifications?\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bsummary\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bdoes\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})\s+have\b",
#         r"\bfuel\s+type\s+of\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
#         r"\bengine\s+capacity\s+of\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
#     ]
#
#     for pat in patterns:
#         m = re.search(pat, t)
#         if not m:
#             continue
#         cand = (m.group(1) or "").strip()
#         cand = re.sub(r"\s+", " ", cand).strip()
#         cand = re.sub(r"[?.!,;:]+$", "", cand).strip()
#         if cand and len(cand) >= 3:
#             return cand
#
#     if "toyota " in t:
#         m2 = re.search(r"\btoyota\s+([a-z0-9][a-z0-9 \-]{1,40})$", t)
#         if m2:
#             cand = (m2.group(1) or "").strip()
#             cand = re.sub(r"[?.!,;:]+$", "", cand).strip()
#             if cand and len(cand) >= 3:
#                 return cand
#
#     return None
#
#
# def _unknown_model_if_any(user_text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
#     if detect_model_in_text(user_text, full_rows):
#         return None
#
#     cand = _extract_model_candidate(user_text)
#     if not cand:
#         return None
#
#     known = _known_model_norms(full_rows)
#     if _norm_model_name(cand) in known:
#         return None
#
#     return cand
#
#
# def _split_compare_candidates(user_text: str) -> List[str]:
#     t = _low(user_text)
#     t = re.sub(r"\b(compare|comparison|difference|between)\b", " ", t)
#     t = re.sub(r"\s+", " ", t).strip()
#
#     for sep in (r"\bvs\b", r"\bversus\b", r"\band\b", r"\bor\b", r"\bwith\b"):
#         if re.search(sep, t):
#             parts = re.split(sep, t, maxsplit=1)
#             if len(parts) == 2:
#                 left = parts[0].strip()
#                 right = parts[1].strip()
#                 left = re.sub(r"[?.!,;:]+$", "", left).strip()
#                 right = re.sub(r"[?.!,;:]+$", "", right).strip()
#                 cands = []
#                 if left:
#                     cands.append(left)
#                 if right:
#                     cands.append(right)
#                 return cands
#
#     return []
#
#
# # =========================
# # 5: System message classification
# # =========================
#
# def _is_small_talk(text: str) -> bool:
#     t = (text or "").strip().lower()
#     exact = {"hi", "hello", "hey", "hii", "thanks", "thank you", "ty", "ok", "okay", "bye", "goodbye"}
#     if t in exact:
#         return True
#     for p in ("hi ", "hello ", "hey ", "thanks ", "thank you "):
#         if t.startswith(p):
#             return True
#     return False
#
#
# def _welcome_text() -> str:
#     return (
#         "Hello! Welcome to Toyota Cambodia. I'm here to help you.\n\n"
#         "You can ask me about:\n"
#         "- Price and specs of any Toyota model\n"
#         "- Features (CarPlay, 360 camera, airbags, seats)\n"
#         "- Compare two models\n"
#         "- Recommendations based on your budget\n"
#         "- Pre-owned / used listings\n\n"
#         "What would you like to know?"
#     )
#
#
# def _is_not_answerable(text: str) -> bool:
#     t = _low(text)
#
#     if re.search(r"\b0[-–]100\b|\b0\s+to\s+100\b|\bacceleration\b", t):
#         return True
#
#     if re.search(r"\b(best|most popular|popular)\b", t):
#         has_budget = extract_budget(text) is not None or any(k in t for k in ["under", "below", "less than", "budget", "max"])
#         has_body = extract_body_type(text) is not None or any(k in t for k in ["suv", "sedan", "pickup", "mpv", "bus"])
#         if not has_budget and not has_body:
#             if "cambodia" in t or "overall" in t or "toyota" in t:
#                 return True
#
#     if "best car" in t and ("cambodia" in t or "overall" in t):
#         return True
#
#     return False
#
#
# def _is_general_knowledge_question(user_text: str, full_rows: List[Dict[str, Any]]) -> bool:
#     t = _low(user_text)
#
#     if detect_model_in_text(user_text, full_rows):
#         return False
#
#     ask_form = (
#         t.startswith("what is")
#         or t.startswith("what's")
#         or t.startswith("how does")
#         or t.startswith("how do")
#         or t.startswith("why")
#         or "benefit" in t
#         or "maintenance cost" in t
#         or "fuel efficient" in t
#         or "battery lifespan" in t
#     )
#     if not ask_form:
#         return False
#
#     terms = [
#         "hybrid technology",
#         "hybrid",
#         "hev",
#         "ev",
#         "electric vehicle",
#         "toyota safety sense",
#         "safety sense",
#         "blind spot monitor",
#         "blind spot monitoring",
#         "bsm",
#         "adaptive cruise control",
#         "regenerative braking",
#         "regen braking",
#         "fuel efficient",
#         "maintenance cost",
#         "battery lifespan",
#     ]
#     return any(term in t for term in terms)
#
#
# def _is_warranty_or_services_info_question(user_text: str) -> bool:
#     t = _low(user_text)
#     if re.search(r"\b(warranty|guarantee|coverage|covered|oem)\b", t):
#         return True
#
#     if re.search(
#         r"\b(service\s+packages?|servicing\s+packages?|servicing|maintenance|repair|service\s+center|service\s+centre|workshop)\b",
#         t,
#     ):
#         return True
#
#     return False
#
#
# def _looks_like_preowned_listing_query(user_text: str) -> bool:
#     t = _low(user_text)
#
#     if re.search(r"\b(what is|what's|how does|how do|explain|about the|tell me about)\b", t) and re.search(
#         r"\b(program|programme|certification|certified program|cpo program)\b", t
#     ):
#         return False
#
#     strong_terms = [
#         "preowned",
#         "pre-owned",
#         "pre owned",
#         "used",
#         "second hand",
#         "certified",
#         "cpo",
#         "toyota certified",
#         "listing",
#         "listings",
#         "plate",
#         "vin",
#         "odometer",
#         "mileage",
#     ]
#     if any(k in t for k in strong_terms):
#         return True
#
#     if re.search(r"\bpp-\d", t) or re.search(r"\b[a-z]{1,3}-[a-z]?-?\d", t):
#         return True
#
#     if "km" in t:
#         if re.search(r"\b(20\d{2}|price|\$|usd|year|mileage|odometer)\b", t):
#             return True
#
#     return False
#
#
# def _is_compare_intent(text: str) -> bool:
#     t = _low(text)
#     if re.search(r"\bcompare\b", t):
#         return True
#     if re.search(r"\bvs\b", t):
#         return True
#     if re.search(r"\bversus\b", t):
#         return True
#     if re.search(r"\bdifference\b", t) and re.search(r"\bbetween\b", t):
#         return True
#     if re.search(r"\bwhich\b.*\bbetter\b", t):
#         return True
#     if re.search(r"\bbetter\b", t) and re.search(r"\bor\b", t):
#         return True
#     if re.search(r"\b(bigger|larger|smaller|heavier|faster|more spacious)\b", t):
#         return True
#     return False
#
#
# def _extract_compare_models(user_text: str, full_rows: List[Dict[str, Any]]) -> List[str]:
#     models = detect_models_in_text(user_text, full_rows, max_models=2)
#     if len(models) >= 2:
#         return models[:2]
#
#     low = _low(user_text)
#
#     m = re.search(r"\bbetween\s+(.*?)\s+\band\s+(.*)$", low)
#     if m:
#         left = (m.group(1) or "").strip()
#         right = (m.group(2) or "").strip()
#         a = detect_model_in_text(left, full_rows)
#         b = detect_model_in_text(right, full_rows)
#         if a and b and a != b:
#             return [a, b]
#
#     m2 = re.search(r"^(.*?)\s+\bor\s+(.*)$", low)
#     if m2:
#         left = (m2.group(1) or "").strip()
#         right = (m2.group(2) or "").strip()
#         a = detect_model_in_text(left, full_rows)
#         b = detect_model_in_text(right, full_rows)
#         if a and b and a != b:
#             return [a, b]
#
#     for sep in (r"\bvs\b", r"\bversus\b", r"\bwith\b", r"\band\b"):
#         parts = re.split(sep, low, maxsplit=1)
#         if len(parts) != 2:
#             continue
#         left = parts[0].strip()
#         right = parts[1].strip()
#         a = detect_model_in_text(left, full_rows)
#         b = detect_model_in_text(right, full_rows)
#         if a and b and a != b:
#             return [a, b]
#
#     one = detect_model_in_text(user_text, full_rows)
#     return [one] if one else []
#
#
# def _do_compare(full_rows: List[Dict[str, Any]], a: str, b: str) -> Dict[str, Any]:
#     row_a = find_row_by_model(full_rows, a)
#     row_b = find_row_by_model(full_rows, b)
#
#     if not row_a or not row_b:
#         missing = a if not row_a else b
#         msg = f"I couldn't find '{missing}' in the dataset."
#         return {"answer_type": "csv_compare", "text": msg, "facts": [msg], "sources": []}
#
#     def v(row, *keys):
#         for key in keys:
#             val = row.get(key)
#             if val is not None and str(val).strip() not in ("", "N/A"):
#                 return str(val).strip()
#         return "N/A"
#
#     def yn(row, *keys):
#         val = v(row, *keys).lower()
#         if val in ("yes", "included", "available", "standard"):
#             return "Yes"
#         if val in ("no", "not available", "not included"):
#             return "No"
#         if val == "n/a":
#             return "N/A"
#         return val.title()
#
#     name_a = row_a.get("model") or a
#     name_b = row_b.get("model") or b
#     price_a = format_price_usd(row_a.get("price_usd"))
#     price_b = format_price_usd(row_b.get("price_usd"))
#
#     lines = [
#         f"Here is a detailed comparison: {name_a} vs {name_b}",
#         "",
#         "Core Specs",
#         f"- Price: {price_a} vs {price_b}",
#         f"- Body type: {v(row_a, 'body_type')} vs {v(row_b, 'body_type')}",
#         f"- Fuel: {v(row_a, 'fuel').title()} vs {v(row_b, 'fuel').title()}",
#         f"- Seats: {v(row_a, 'seats')} vs {v(row_b, 'seats')}",
#         f"- Transmission: {v(row_a, 'spec_transmission', 'spec_transmission_type')} vs {v(row_b, 'spec_transmission', 'spec_transmission_type')}",
#         f"- Engine: {v(row_a, 'spec_engine_type')} vs {v(row_b, 'spec_engine_type')}",
#         f"- Displacement: {v(row_a, 'spec_displacement')} vs {v(row_b, 'spec_displacement')}",
#         f"- Ground clearance: {v(row_a, 'spec_ground_clearance')} vs {v(row_b, 'spec_ground_clearance')}",
#         "",
#         "Safety and Technology",
#         f"- Apple CarPlay/Android Auto: {yn(row_a, 'spec_apple_carplay_and_android_auto', 'spec_apple_carplay_or_android_auto')} vs {yn(row_b, 'spec_apple_carplay_and_android_auto', 'spec_apple_carplay_or_android_auto')}",
#         f"- 360 Camera (PVM): {yn(row_a, 'spec_panoramic_view_monitor_pvm')} vs {yn(row_b, 'spec_panoramic_view_monitor_pvm')}",
#         f"- Reverse Camera: {yn(row_a, 'spec_reverse_camera')} vs {yn(row_b, 'spec_reverse_camera')}",
#         f"- Blind Spot Monitor: {yn(row_a, 'spec_blind_spot_monitor_bsm')} vs {yn(row_b, 'spec_blind_spot_monitor_bsm')}",
#         f"- Cruise Control: {yn(row_a, 'spec_cruise_control', 'spec_dynamic_radar_cruise_control_drcc')} vs {yn(row_b, 'spec_cruise_control', 'spec_dynamic_radar_cruise_control_drcc')}",
#         f"- Wireless Charging: {yn(row_a, 'spec_wireless_charging', 'spec_wireless_charger')} vs {yn(row_b, 'spec_wireless_charging', 'spec_wireless_charger')}",
#         f"- Smart Entry: {yn(row_a, 'spec_smart_entry')} vs {yn(row_b, 'spec_smart_entry')}",
#         f"- Head-Up Display: {yn(row_a, 'spec_headup_display_hud')} vs {yn(row_b, 'spec_headup_display_hud')}",
#         f"- SRS Airbags: {v(row_a, 'spec_srs_airbags')} vs {v(row_b, 'spec_srs_airbags')}",
#     ]
#
#     summary: List[str] = []
#     try:
#         p_a = float(str(row_a.get("price_usd", "0")).replace(",", "").replace("$", "") or 0)
#         p_b = float(str(row_b.get("price_usd", "0")).replace(",", "").replace("$", "") or 0)
#         if p_a > 0 and p_b > 0 and p_a != p_b:
#             cheaper = name_a if p_a < p_b else name_b
#             diff = abs(p_a - p_b)
#             summary.append(f"The {cheaper} is ${diff:,.0f} cheaper.")
#     except Exception:
#         pass
#
#     try:
#         s_a = float(v(row_a, "seats") if v(row_a, "seats") != "N/A" else "0")
#         s_b = float(v(row_b, "seats") if v(row_b, "seats") != "N/A" else "0")
#         if s_a > 0 and s_b > 0 and s_a != s_b:
#             more = name_a if s_a > s_b else name_b
#             summary.append(f"The {more} has more seating capacity.")
#     except Exception:
#         pass
#
#     fuel_a = v(row_a, "fuel").lower()
#     fuel_b = v(row_b, "fuel").lower()
#     if fuel_a != fuel_b and "n/a" not in (fuel_a, fuel_b):
#         summary.append(f"{name_a} uses {fuel_a} while {name_b} uses {fuel_b}.")
#
#     if summary:
#         lines += ["", "Summary", " ".join(summary)]
#
#     txt = "\n".join(lines)
#     sources: List[str] = []
#     for row in [row_a, row_b]:
#         url = row.get("url")
#         if url and url not in sources:
#             sources.append(url)
#
#     return {"answer_type": "csv_compare", "text": txt, "facts": [txt], "sources": sources}
#
#
# def _looks_like_filter(user_text: str, full_rows: List[Dict[str, Any]]) -> bool:
#     t = _low(user_text)
#     has_budget = extract_budget(user_text) is not None or any(k in t for k in ["under", "below", "less than", "budget", "max"])
#     has_body = extract_body_type(user_text) is not None or any(k in t for k in ["suv", "sedan", "pickup", "mpv", "bus"])
#     has_fuel = extract_fuel(user_text) is not None or any(k in t for k in ["gasoline", "petrol", "diesel", "hybrid", "hev", "ev", "electric"])
#     has_model = detect_model_in_text(user_text, full_rows) is not None
#     return (not has_model) and has_budget and (has_body or has_fuel)
#
#
# def _is_gibberish(text: str) -> bool:
#     t = (text or "").strip().lower()
#     if not t:
#         return True
#     if len(t) <= 2 and not any(c.isdigit() for c in t):
#         return True
#     if re.fullmatch(r"[\W_]+", t):
#         return True
#     if len(set(t)) <= 2 and len(t) >= 6:
#         return True
#     letters = re.sub(r"[^a-z]", "", t)
#     if len(letters) >= 6:
#         vowels = sum(1 for c in letters if c in "aeiouy")
#         if vowels / max(len(letters), 1) > 0.75:
#             return True
#     return False
#
#
# def _is_off_topic(text: str, full_rows: List[Dict[str, Any]]) -> bool:
#     t = (text or "").lower()
#     if detect_model_in_text(text, full_rows):
#         return False
#
#     car_keywords = [
#         "price",
#         "cost",
#         "spec",
#         "specs",
#         "feature",
#         "engine",
#         "fuel",
#         "seat",
#         "suv",
#         "sedan",
#         "pickup",
#         "mpv",
#         "hybrid",
#         "diesel",
#         "gasoline",
#         "ev",
#         "preowned",
#         "pre-owned",
#         "used",
#         "mileage",
#         "compare",
#         "recommend",
#         "budget",
#         "warranty",
#         "service",
#     ]
#     if any(k in t for k in car_keywords):
#         return False
#
#     off_topic = ["joke", "song", "movie", "weather", "love", "dating", "translate", "math", "game"]
#     return any(k in t for k in off_topic)
#
#
# def _is_service_company_rag_intent(user_text: str) -> bool:
#     t = _low(user_text)
#
#     if re.search(r"\b(service|services|serviced|servicing|maintenance|repair|appointment|book|booking|schedule)\b", t):
#         return True
#     if re.search(r"\b(branch|branches|showroom|dealer|dealership|service center|workshop|contact|hotline|phone|address|location)\b", t):
#         return True
#     if re.search(r"\b(company profile|profile|history|mission|vision|official distributor|distributor)\b", t):
#         return True
#     if re.search(r"\b(toyota plus|genuine parts|parts policy|warranty|guarantee|coverage)\b", t):
#         return True
#     if re.search(r"\bservice\s*[a-d]\b.*\b(price|cost)\b", t):
#         return True
#     if re.search(r"\b(certified\s+pre.?owned|cpo|pre.?owned\s+program|preowned\s+program)\b", t):
#         return True
#     if re.search(r"\bhow\s+(often|frequently|long)\b", t) and re.search(r"\b(service|serviced|maintenance|maintain)\b", t):
#         return True
#     if re.search(r"\b(provide|provides|offer|offers)\b", t) and "toyota" in t:
#         return True
#
#     return False
#
#
# # =========================
# # 8: Main chat turn
# # =========================
#
# def chat_turn(
#     user_text: str,
#     state: Dict[str, Any],
#     full_rows: List[Dict[str, Any]],
#     rag_engine: Any,
#     preowned_engine: PreownedEngine,
#     debug: bool = False,
# ) -> Dict[str, Any]:
#
#     if not state:
#         _reset_state(state)
#
#     user_text = _clean(user_text)
#     if not user_text:
#         return _sys("Please type a question.")
#
#     user_text = _resolve_with_history(user_text, state, full_rows)
#     t0 = _low(user_text)
#
#     # Reset
#     if t0 in {"/reset", "reset"}:
#         _reset_state(state)
#         return _sys("Reset done.")
#
#     # Small talk
#     if _is_small_talk(user_text):
#         if t0 in {"thanks", "thank you", "ty"}:
#             return _sys("You're welcome. What would you like to know about Toyota Cambodia?")
#         if t0 in {"bye", "goodbye"}:
#             return _sys("Bye. If you need anything about Toyota models, price, specs, or services, just ask.")
#         return _sys(_welcome_text())
#
#     # Gibberish
#     if _is_gibberish(user_text):
#         return _sys(
#             "Please ask a Toyota vehicle question such as price, specs, features, comparison, recommendation, "
#             "pre-owned listings, warranty, or service information."
#         )
#
#     # Off-topic
#     if _is_off_topic(user_text, full_rows):
#         return _sys(
#             "I can only help with Toyota Cambodia vehicle information such as price, specs, features, "
#             "comparison, recommendation, pre-owned listings, warranty, or service information."
#         )
#
#     # Not supported
#     if _is_not_answerable(user_text):
#         return _sys(
#             "I don't have that information in our dataset. "
#             "Please ask about Toyota models, price, specs, features, comparison, recommendations, or services."
#         )
#
#     # General knowledge -> RAG (real)
#     if _is_general_knowledge_question(user_text, full_rows) and getattr(rag_engine, "available", False):
#         out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
#         out["text"] = _remove_markdown_bold(style_answer(user_text, out, DEFAULT_STYLE))
#         return _pipe(out, "RAG")
#
#     # Service/company topics -> RAG (real)
#     if (_is_warranty_or_services_info_question(user_text) or _is_service_company_rag_intent(user_text)) and getattr(rag_engine, "available", False):
#         out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
#         out["text"] = _remove_markdown_bold(out.get("text") or "")
#         return _pipe(out, "RAG")
#
#     # Preowned
#     # Preowned
#     if is_preowned_intent(user_text) and _looks_like_preowned_listing_query(user_text):
#         _cancel_reco_flow(state)
#
#         result = preowned_engine.query(user_text, top_k=10)
#         ans = preowned_engine.format_answer(result)
#
#         text = str(ans.get("text") or "").strip()
#         sources = ans.get("sources") or []
#
#         if not text:
#             if sources:
#                 lines = ["Here are Toyota Certified Pre-Owned listings:"]
#                 for i, s in enumerate(sources[:10], start=1):
#                     lines.append(f"{i}. {s}")
#                 text = "\n".join(lines)
#             else:
#                 text = "Sorry, I couldn't find any pre-owned listings."
#
#         res = {"answer_type": "preowned", "text": text, "facts": [text], "sources": sources}
#         styled = style_answer(user_text, res, DEFAULT_STYLE)
#         if styled and styled.strip():
#             res["text"] = styled
#         return _pipe(res, "PREOWNED_RAG")
#
#     # # Service / company knowledge -> RAG
#     # if _is_warranty_or_services_info_question(user_text) or _is_service_company_rag_intent(user_text):
#     #     out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
#     #     out["text"] = style_answer(user_text, out, DEFAULT_STYLE)
#     #     return _pipe(out, "RAG")
#
#     # Track last model mention
#     mentioned = detect_model_in_text(user_text, full_rows)
#     if mentioned:
#         state["last_model"] = mentioned
#
#     # Compare
#     if _is_compare_intent(user_text):
#         models = _extract_compare_models(user_text, full_rows)
#
#         if len(models) >= 2:
#             _cancel_reco_flow(state)
#             return _pipe(_do_compare(full_rows, models[0], models[1]), "CSV_METHOD")
#
#         if len(models) == 1:
#             msg = (
#                 f"I found {models[0]} in our dataset, but couldn't identify the second model. "
#                 f"It may not be available in Toyota Cambodia's current lineup. "
#                 f"Try: compare Veloz vs Vios"
#             )
#             return _pipe({"answer_type": "csv_compare", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#         # If no dataset models found, try detect unknown compare candidates
#         cands = _split_compare_candidates(user_text)
#         unknowns = []
#         known_norms = _known_model_norms(full_rows)
#         for c in cands[:2]:
#             nn = _norm_model_name(c)
#             if nn and nn not in known_norms:
#                 unknowns.append(c)
#
#         if unknowns:
#             if len(unknowns) == 2:
#                 msg = (
#                     f"I couldn't find {unknowns[0].title()} and {unknowns[1].title()} in the Toyota Cambodia dataset. "
#                     f"Try: compare Veloz vs Vios, Fortuner vs Hilux, Corolla Cross vs Yaris Cross."
#                 )
#             else:
#                 msg = (
#                     f"I couldn't find {unknowns[0].title()} in the Toyota Cambodia dataset. "
#                     f"Try: compare Veloz vs Vios, Fortuner vs Hilux, Corolla Cross vs Yaris Cross."
#                 )
#             return _pipe({"answer_type": "csv_compare", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#         msg = "Which two Toyota models do you want to compare? Example: compare Veloz vs Vios"
#         return _pipe({"answer_type": "csv_compare", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#     # Specs
#     if is_spec_intent(user_text):
#         unk = _unknown_model_if_any(user_text, full_rows)
#         if unk:
#             msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
#             return _pipe({"answer_type": "csv_specs", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#         model = detect_model_in_text(user_text, full_rows) or state.get("last_model")
#         if not model:
#             return _sys("Which model are you asking about?")
#
#         state["last_model"] = model
#         _cancel_reco_flow(state)
#         return _pipe(answer_specs_from_csv(full_rows, model), "CSV_METHOD")
#
#     # Summary
#     if is_summary_intent(user_text):
#         unk = _unknown_model_if_any(user_text, full_rows)
#         if unk:
#             msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
#             return _pipe({"answer_type": "csv_summary", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#         model = detect_model_in_text(user_text, full_rows) or state.get("last_model")
#         if not model:
#             return _sys("Which model are you asking about?")
#
#         state["last_model"] = model
#         _cancel_reco_flow(state)
#         return _pipe(answer_summary_from_csv(full_rows, model), "CSV_METHOD")
#
#     # Price
#     if any(k in t0 for k in ["price", "how much", "cost", "starting price"]):
#         if any(k in t0 for k in ["under", "below", "budget", "less than"]):
#             pass
#         else:
#             unk = _unknown_model_if_any(user_text, full_rows)
#             if unk:
#                 msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
#                 return _pipe({"answer_type": "csv_price", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#             model = resolve_target_model(user_text, state.get("last_model"), full_rows)
#             if not model:
#                 msg = "Which Toyota model price do you want?"
#                 return _pipe({"answer_type": "csv_price", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#             state["last_model"] = model
#             _cancel_reco_flow(state)
#             return _pipe(answer_price_from_csv(full_rows, model), "CSV_METHOD")
#
#     # Recommendation engine
#     is_reco = (
#         is_recommendation_intent(user_text)
#         or state.get("slot_fill_active") is True
#         or _looks_like_filter(user_text, full_rows)
#     )
#
#     if is_reco:
#         b = extract_budget(user_text)
#         s = extract_seats(user_text)
#         f = extract_fuel(user_text)
#         bt = extract_body_type(user_text)
#
#         if b is not None:
#             state["slots"]["max_budget"] = b
#         if s is not None:
#             state["slots"]["min_seats"] = s
#         if f:
#             state["slots"]["fuel"] = f
#         if bt:
#             state["slots"]["body_type"] = bt
#
#         missing = _missing_slots(state["slots"])
#         if missing:
#             state["slot_fill_active"] = True
#             if "budget" in missing:
#                 return _csv_msg("Tell me your budget (USD). Example: budget 40000")
#             if "body" in missing:
#                 return _csv_msg("What body type do you want? (SUV / Sedan / Pickup / MPV / Bus)")
#             if "fuel" in missing:
#                 return _csv_msg("What fuel do you prefer? (Gasoline / Diesel / Hybrid / EV)")
#             return _csv_msg("Please provide: " + ", ".join(missing))
#
#         max_budget = float(state["slots"]["max_budget"])
#         min_seats = int(state["slots"]["min_seats"] or 0)
#         fuel = state["slots"]["fuel"]
#         body_type = state["slots"]["body_type"]
#
#         verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
#         res = build_reco_answer(verified, possible, max_items=5)
#         _cancel_reco_flow(state)
#         return _pipe(res, "CSV_METHOD")
#
#     # Feature Q&A
#     feature_key = detect_feature_key(user_text)
#     if feature_key:
#         unk = _unknown_model_if_any(user_text, full_rows)
#         if unk:
#             msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
#             return _pipe({"answer_type": "csv_feature", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#         model = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if not model:
#             msg = "Which Toyota model are you asking about?"
#             return _pipe({"answer_type": "csv_feature", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#         state["last_model"] = model
#         _cancel_reco_flow(state)
#
#         res = answer_feature_from_csv(full_rows, model, feature_key)
#         if res:
#             return _pipe(res, "CSV_METHOD")
#
#         msg = "That feature is not available in the dataset yet."
#         return _pipe({"answer_type": "csv_feature", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")
#
#     # Final RAG fallback (real)
#     if getattr(rag_engine, "available", False):
#         out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
#         out["text"] = _remove_markdown_bold(out.get("text") or "")
#         styled = _remove_markdown_bold(style_answer(user_text, out, DEFAULT_STYLE))
#         if styled and styled.strip():
#             out["text"] = styled
#         return _pipe(out, "RAG")
#
#     return _unknown_question_response(user_text, state)
#
#
# def render_answer(
#     user_text: str,
#     res: Dict[str, Any],
#     use_llm: bool = False,
#     rewrite_csv: bool = False,
#     debug: bool = False,
# ) -> str:
#     text = str(res.get("answer") or res.get("text") or "").strip()
#     if not text:
#         facts = res.get("facts") or []
#         if isinstance(facts, list) and facts:
#             text = str(facts[0]).strip()
#     if not text:
#         text = "Sorry — I couldn't produce an answer."
#
#     text = _remove_markdown_bold(text)
#
#     sources = [s for s in (res.get("sources") or []) if s]
#     if sources:
#         text += "\nSources: " + ", ".join(sources[:3])
#
#     if debug and res.get("pipeline"):
#         text += f"\n[PIPELINE={res['pipeline']}]"
#
#     # Optional: show RAG evidence in debug
#     if debug and res.get("pipeline") == "RAG" and res.get("evidence"):
#         ev = res.get("evidence") or []
#         lines = []
#         for e in ev[:5]:
#             lines.append(f"- chunk={e.get('chunk_id')} score={e.get('score')} url={e.get('source_url')}")
#         if lines:
#             text += "\nEVIDENCE:\n" + "\n".join(lines)
#
#     return text

# scripts/chat_assistant.py

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent

from scripts.response_style import style_answer, DEFAULT_STYLE
from scripts.llm_client import llm_rewrite

from scripts.csv_engine import (
    detect_feature_key,
    detect_model_in_text,
    detect_models_in_text,
    resolve_target_model,
    answer_feature_from_csv,
    answer_price_from_csv,
    answer_specs_from_csv,
    answer_summary_from_csv,
    is_recommendation_intent,
    is_spec_intent,
    is_summary_intent,
    extract_budget,
    extract_seats,
    extract_fuel,
    extract_body_type,
    filter_cars_split,
    build_reco_answer,
    find_row_by_model,
    format_price_usd,
)

from scripts.preowned_engine import PreownedEngine, is_preowned_intent


class NoRAG:
    available = False

    def __init__(self, rows: List[Dict[str, Any]]):
        self.rows = rows

    def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
        msg = (
            "RAG is not available. Please ask about price, specs, features, comparisons, recommendations, or pre-owned listings."
        )
        return {"answer_type": "rag", "text": msg, "facts": [msg], "sources": []}


def build_rag_engine(rows: List[Dict[str, Any]]):
    from scripts.rag_engine import VehicleRAGEngine
    from scripts.services_rag_engine import ServicesRAGEngine

    llm_model = os.environ.get("RAG_LLM_MODEL") or os.environ.get("OLLAMA_MODEL") or "llama3"
    ollama_url = os.environ.get("OLLAMA_URL") or "http://localhost:11434/api/generate"

    vehicle = VehicleRAGEngine(
        rows,
        llm_model=llm_model,
        ollama_url=ollama_url,
    )

    services = ServicesRAGEngine(
        chroma_dir=_PROJECT_ROOT / "vector_db" / "chroma_services",
        collection_name="services_pages",
        llm_model=llm_model,
        ollama_url=ollama_url,
    )

    class Composite:
        available = True

        def rag_answer(self, user_text: str, last_model_norm: Optional[str] = None) -> Dict[str, Any]:
            if _is_warranty_or_services_info_question(user_text) or _is_service_company_rag_intent(user_text):
                return services.rag_answer(user_text, last_model_norm=last_model_norm)
            return vehicle.rag_answer(user_text, last_model_norm=last_model_norm)

    return Composite()


def build_preowned_engine(preowned_csv_path: Optional[str] = None) -> PreownedEngine:
    return PreownedEngine(csv_path=preowned_csv_path)


def _low(s: Any) -> str:
    return (str(s) or "").strip().lower()


def _clean(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^\s*\d+[\.\)]\s*", "", t)
    t = t.strip('"\'`\u201c\u201d\u2018\u2019')
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _remove_markdown_bold(text: str) -> str:
    if not text:
        return text
    return text.replace("**", "")


def _pipe(res: Dict[str, Any], pipeline: str) -> Dict[str, Any]:
    out = dict(res)
    out["pipeline"] = pipeline
    if "text" not in out:
        out["text"] = out.get("answer") or ""
    if "answer" not in out:
        out["answer"] = out.get("text") or ""
    out["text"] = _remove_markdown_bold(str(out.get("text") or ""))
    out["answer"] = _remove_markdown_bold(str(out.get("answer") or ""))
    return out


def _sys(text: str) -> Dict[str, Any]:
    text = _remove_markdown_bold(text)
    return _pipe({"answer_type": "system", "text": text, "facts": [text], "sources": []}, "SYSTEM")


def _csv_msg(text: str, answer_type: str = "system") -> Dict[str, Any]:
    text = _remove_markdown_bold(text)
    return _pipe({"answer_type": answer_type, "text": text, "facts": [text], "sources": []}, "CSV_METHOD")


def _unknown_question_response(user_text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    t = (user_text or "").lower()
    last_model = state.get("last_model")

    if (
        re.search(r"\b(warranty|guarantee|coverage|covered)\b", t)
        or re.search(r"\b(service|services|servicing|maintenance|repair|package|packages|schedule|workshop|showroom|branch|dealer|contact|hotline)\b", t)
        or re.search(r"\b(certified\s+pre.?owned|cpo)\b", t)
    ):
        hint = (
            "Please ask a Toyota Cambodia question like:\n"
            "- What service packages do you provide?\n"
            "- Where is the service center / showroom?\n"
            "- What is included in Toyota warranty?\n"
            "- Toyota Certified Pre-Owned program details"
        )
        return _sys(hint)

    if last_model:
        hint = (
            f"I'm not sure what you mean, but I was last discussing the {last_model}. "
            f"You can ask me about its price, specs, features, or compare it with another model."
        )
        return _sys(hint)

    if any(k in t for k in ["toyota", "car", "vehicle", "model"]):
        hint = (
            "I can help you with Toyota Cambodia vehicles. Try asking:\n"
            "- Price of Fortuner / specs of Yaris Cross\n"
            "- Compare Raize vs Veloz\n"
            "- Recommend a car under $40,000\n"
            "- Show pre-owned SUV under $35,000"
        )
        return _sys(hint)

    hint = (
        "I'm a Toyota Cambodia assistant. I can help with:\n"
        "- Price and Specs\n"
        "- Features\n"
        "- Compare\n"
        "- Recommend\n"
        "- Pre-owned listings\n"
        "- Service & Warranty"
    )
    return _sys(hint)


def _reset_state(state: Dict[str, Any]) -> None:
    state.clear()
    state.update(
        {
            "last_model": None,
            "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
            "slot_fill_active": False,
            "conversation_history": [],
        }
    )


def _resolve_with_history(user_text: str, state: Dict[str, Any], full_rows) -> str:
    t = user_text.lower().strip()
    last_model = state.get("last_model")
    has_pronoun = bool(re.search(r"\b(it|its|that|this|the car|the model|the vehicle)\b", t))
    has_model = bool(detect_model_in_text(user_text, full_rows))

    if has_pronoun and not has_model and last_model:
        user_text = re.sub(r"\b(it|its)\b", last_model, user_text, flags=re.IGNORECASE)

    return user_text


def _cancel_reco_flow(state: Dict[str, Any]) -> None:
    state["slot_fill_active"] = False
    state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}


def _missing_slots(slots: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    if slots.get("max_budget") is None:
        missing.append("budget")
    if not slots.get("body_type"):
        missing.append("body")
    if not slots.get("fuel"):
        missing.append("fuel")
    return missing


def _norm_model_name(s: str) -> str:
    x = (s or "").strip().lower()
    x = re.sub(r"[^a-z0-9]+", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x


def _known_model_norms(full_rows: List[Dict[str, Any]]) -> set:
    out = set()
    for r in full_rows:
        m = str(r.get("model") or "").strip()
        if m:
            out.add(_norm_model_name(m))
    return out


def _extract_model_candidate(user_text: str) -> Optional[str]:
    t = _low(user_text)

    patterns = [
        r"\bprice\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bhow\s+much\s+is\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bcost\s+of\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bstarting\s+price\s+(?:of|for)\s+([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bspecs?\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bspecifications?\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bsummary\s+of\s+([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bdoes\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})\s+have\b",
        r"\bfuel\s+type\s+of\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
        r"\bengine\s+capacity\s+of\s+(?:toyota\s+)?([a-z0-9][a-z0-9 \-]{1,40})$",
    ]

    for pat in patterns:
        m = re.search(pat, t)
        if not m:
            continue
        cand = (m.group(1) or "").strip()
        cand = re.sub(r"\s+", " ", cand).strip()
        cand = re.sub(r"[?.!,;:]+$", "", cand).strip()
        if cand and len(cand) >= 3:
            return cand

    if "toyota " in t:
        m2 = re.search(r"\btoyota\s+([a-z0-9][a-z0-9 \-]{1,40})$", t)
        if m2:
            cand = (m2.group(1) or "").strip()
            cand = re.sub(r"[?.!,;:]+$", "", cand).strip()
            if cand and len(cand) >= 3:
                return cand

    return None


def _unknown_model_if_any(user_text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
    if detect_model_in_text(user_text, full_rows):
        return None

    cand = _extract_model_candidate(user_text)
    if not cand:
        return None

    known = _known_model_norms(full_rows)
    if _norm_model_name(cand) in known:
        return None

    return cand


def _split_compare_candidates(user_text: str) -> List[str]:
    t = _low(user_text)
    t = re.sub(r"\b(compare|comparison|difference|between)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    for sep in (r"\bvs\b", r"\bversus\b", r"\band\b", r"\bor\b", r"\bwith\b"):
        if re.search(sep, t):
            parts = re.split(sep, t, maxsplit=1)
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()
                left = re.sub(r"[?.!,;:]+$", "", left).strip()
                right = re.sub(r"[?.!,;:]+$", "", right).strip()
                cands = []
                if left:
                    cands.append(left)
                if right:
                    cands.append(right)
                return cands

    return []


def _is_small_talk(text: str) -> bool:
    t = (text or "").strip().lower()
    exact = {"hi", "hello", "hey", "hii", "thanks", "thank you", "ty", "ok", "okay", "bye", "goodbye"}
    if t in exact:
        return True
    for p in ("hi ", "hello ", "hey ", "thanks ", "thank you "):
        if t.startswith(p):
            return True
    return False


def _welcome_text() -> str:
    return (
        "Hello! Welcome to Toyota Cambodia. I'm here to help you.\n\n"
        "You can ask me about:\n"
        "- Price and specs of any Toyota model\n"
        "- Features (CarPlay, 360 camera, airbags, seats)\n"
        "- Compare two models\n"
        "- Recommendations based on your budget\n"
        "- Pre-owned / used listings\n\n"
        "What would you like to know?"
    )


def _is_not_answerable(text: str) -> bool:
    t = _low(text)

    if re.search(r"\b0[-–]100\b|\b0\s+to\s+100\b|\bacceleration\b", t):
        return True

    if re.search(r"\b(best|most popular|popular)\b", t):
        has_budget = extract_budget(text) is not None or any(k in t for k in ["under", "below", "less than", "budget", "max"])
        has_body = extract_body_type(text) is not None or any(k in t for k in ["suv", "sedan", "pickup", "mpv", "bus"])
        if not has_budget and not has_body:
            if "cambodia" in t or "overall" in t or "toyota" in t:
                return True

    if "best car" in t and ("cambodia" in t or "overall" in t):
        return True

    return False


def _is_general_knowledge_question(user_text: str, full_rows: List[Dict[str, Any]]) -> bool:
    t = _low(user_text)

    if detect_model_in_text(user_text, full_rows):
        return False

    ask_form = (
        t.startswith("what is")
        or t.startswith("what's")
        or t.startswith("how does")
        or t.startswith("how do")
        or t.startswith("why")
        or "benefit" in t
        or "maintenance cost" in t
        or "fuel efficient" in t
        or "battery lifespan" in t
    )
    if not ask_form:
        return False

    terms = [
        "hybrid technology",
        "hybrid",
        "hev",
        "ev",
        "electric vehicle",
        "toyota safety sense",
        "safety sense",
        "blind spot monitor",
        "blind spot monitoring",
        "bsm",
        "adaptive cruise control",
        "regenerative braking",
        "regen braking",
        "fuel efficient",
        "maintenance cost",
        "battery lifespan",
    ]
    return any(term in t for term in terms)


def _is_warranty_or_services_info_question(user_text: str) -> bool:
    t = _low(user_text)
    if re.search(r"\b(warranty|guarantee|coverage|covered|oem)\b", t):
        return True

    if re.search(
        r"\b(service\s+packages?|servicing\s+packages?|servicing|maintenance|repair|service\s+center|service\s+centre|workshop)\b",
        t,
    ):
        return True

    return False


def _looks_like_preowned_listing_query(user_text: str) -> bool:
    t = _low(user_text)

    if re.search(r"\b(what is|what's|how does|how do|explain|about the|tell me about)\b", t) and re.search(
        r"\b(program|programme|certification|certified program|cpo program)\b", t
    ):
        return False

    strong_terms = [
        "preowned",
        "pre-owned",
        "pre owned",
        "used",
        "second hand",
        "certified",
        "cpo",
        "toyota certified",
        "listing",
        "listings",
        "plate",
        "vin",
        "odometer",
        "mileage",
    ]
    if any(k in t for k in strong_terms):
        return True

    if re.search(r"\bpp-\d", t) or re.search(r"\b[a-z]{1,3}-[a-z]?-?\d", t):
        return True

    if "km" in t:
        if re.search(r"\b(20\d{2}|price|\$|usd|year|mileage|odometer)\b", t):
            return True

    return False


def _is_compare_intent(text: str) -> bool:
    t = _low(text)
    if re.search(r"\bcompare\b", t):
        return True
    if re.search(r"\bvs\b", t):
        return True
    if re.search(r"\bversus\b", t):
        return True
    if re.search(r"\bdifference\b", t) and re.search(r"\bbetween\b", t):
        return True
    if re.search(r"\bwhich\b.*\bbetter\b", t):
        return True
    if re.search(r"\bbetter\b", t) and re.search(r"\bor\b", t):
        return True
    if re.search(r"\b(bigger|larger|smaller|heavier|faster|more spacious)\b", t):
        return True
    return False


def _extract_compare_models(user_text: str, full_rows: List[Dict[str, Any]]) -> List[str]:
    models = detect_models_in_text(user_text, full_rows, max_models=2)
    if len(models) >= 2:
        return models[:2]

    low = _low(user_text)

    m = re.search(r"\bbetween\s+(.*?)\s+\band\s+(.*)$", low)
    if m:
        left = (m.group(1) or "").strip()
        right = (m.group(2) or "").strip()
        a = detect_model_in_text(left, full_rows)
        b = detect_model_in_text(right, full_rows)
        if a and b and a != b:
            return [a, b]

    m2 = re.search(r"^(.*?)\s+\bor\s+(.*)$", low)
    if m2:
        left = (m2.group(1) or "").strip()
        right = (m2.group(2) or "").strip()
        a = detect_model_in_text(left, full_rows)
        b = detect_model_in_text(right, full_rows)
        if a and b and a != b:
            return [a, b]

    for sep in (r"\bvs\b", r"\bversus\b", r"\bwith\b", r"\band\b"):
        parts = re.split(sep, low, maxsplit=1)
        if len(parts) != 2:
            continue
        left = parts[0].strip()
        right = parts[1].strip()
        a = detect_model_in_text(left, full_rows)
        b = detect_model_in_text(right, full_rows)
        if a and b and a != b:
            return [a, b]

    one = detect_model_in_text(user_text, full_rows)
    return [one] if one else []


def _do_compare(full_rows: List[Dict[str, Any]], a: str, b: str) -> Dict[str, Any]:
    row_a = find_row_by_model(full_rows, a)
    row_b = find_row_by_model(full_rows, b)

    if not row_a or not row_b:
        missing = a if not row_a else b
        msg = f"I couldn't find '{missing}' in the dataset."
        return {"answer_type": "csv_compare", "text": msg, "facts": [msg], "sources": []}

    def v(row, *keys):
        for key in keys:
            val = row.get(key)
            if val is not None and str(val).strip() not in ("", "N/A"):
                return str(val).strip()
        return "N/A"

    def yn(row, *keys):
        val = v(row, *keys).lower()
        if val in ("yes", "included", "available", "standard"):
            return "Yes"
        if val in ("no", "not available", "not included"):
            return "No"
        if val == "n/a":
            return "N/A"
        return val.title()

    name_a = row_a.get("model") or a
    name_b = row_b.get("model") or b
    price_a = format_price_usd(row_a.get("price_usd"))
    price_b = format_price_usd(row_b.get("price_usd"))

    lines = [
        f"Here is a detailed comparison: {name_a} vs {name_b}",
        "",
        "Core Specs",
        f"- Price: {price_a} vs {price_b}",
        f"- Body type: {v(row_a, 'body_type')} vs {v(row_b, 'body_type')}",
        f"- Fuel: {v(row_a, 'fuel').title()} vs {v(row_b, 'fuel').title()}",
        f"- Seats: {v(row_a, 'seats')} vs {v(row_b, 'seats')}",
        f"- Transmission: {v(row_a, 'spec_transmission', 'spec_transmission_type')} vs {v(row_b, 'spec_transmission', 'spec_transmission_type')}",
        f"- Engine: {v(row_a, 'spec_engine_type')} vs {v(row_b, 'spec_engine_type')}",
        f"- Displacement: {v(row_a, 'spec_displacement')} vs {v(row_b, 'spec_displacement')}",
        f"- Ground clearance: {v(row_a, 'spec_ground_clearance')} vs {v(row_b, 'spec_ground_clearance')}",
        "",
        "Safety and Technology",
        f"- Apple CarPlay/Android Auto: {yn(row_a, 'spec_apple_carplay_and_android_auto', 'spec_apple_carplay_or_android_auto')} vs {yn(row_b, 'spec_apple_carplay_and_android_auto', 'spec_apple_carplay_or_android_auto')}",
        f"- 360 Camera (PVM): {yn(row_a, 'spec_panoramic_view_monitor_pvm')} vs {yn(row_b, 'spec_panoramic_view_monitor_pvm')}",
        f"- Reverse Camera: {yn(row_a, 'spec_reverse_camera')} vs {yn(row_b, 'spec_reverse_camera')}",
        f"- Blind Spot Monitor: {yn(row_a, 'spec_blind_spot_monitor_bsm')} vs {yn(row_b, 'spec_blind_spot_monitor_bsm')}",
        f"- Cruise Control: {yn(row_a, 'spec_cruise_control', 'spec_dynamic_radar_cruise_control_drcc')} vs {yn(row_b, 'spec_cruise_control', 'spec_dynamic_radar_cruise_control_drcc')}",
        f"- Wireless Charging: {yn(row_a, 'spec_wireless_charging', 'spec_wireless_charger')} vs {yn(row_b, 'spec_wireless_charging', 'spec_wireless_charger')}",
        f"- Smart Entry: {yn(row_a, 'spec_smart_entry')} vs {yn(row_b, 'spec_smart_entry')}",
        f"- Head-Up Display: {yn(row_a, 'spec_headup_display_hud')} vs {yn(row_b, 'spec_headup_display_hud')}",
        f"- SRS Airbags: {v(row_a, 'spec_srs_airbags')} vs {v(row_b, 'spec_srs_airbags')}",
    ]

    txt = "\n".join(lines)
    sources: List[str] = []
    for row in [row_a, row_b]:
        url = row.get("url")
        if url and url not in sources:
            sources.append(url)

    return {"answer_type": "csv_compare", "text": txt, "facts": [txt], "sources": sources}


def _looks_like_filter(user_text: str, full_rows: List[Dict[str, Any]]) -> bool:
    t = _low(user_text)
    has_budget = extract_budget(user_text) is not None or any(k in t for k in ["under", "below", "less than", "budget", "max"])
    has_body = extract_body_type(user_text) is not None or any(k in t for k in ["suv", "sedan", "pickup", "mpv", "bus"])
    has_fuel = extract_fuel(user_text) is not None or any(k in t for k in ["gasoline", "petrol", "diesel", "hybrid", "hev", "ev", "electric"])
    has_model = detect_model_in_text(user_text, full_rows) is not None
    return (not has_model) and has_budget and (has_body or has_fuel)


def _is_gibberish(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if len(t) <= 2 and not any(c.isdigit() for c in t):
        return True
    if re.fullmatch(r"[\W_]+", t):
        return True
    if len(set(t)) <= 2 and len(t) >= 6:
        return True
    letters = re.sub(r"[^a-z]", "", t)
    if len(letters) >= 6:
        vowels = sum(1 for c in letters if c in "aeiouy")
        if vowels / max(len(letters), 1) > 0.75:
            return True
    return False


def _is_off_topic(text: str, full_rows: List[Dict[str, Any]]) -> bool:
    t = (text or "").lower()
    if detect_model_in_text(text, full_rows):
        return False

    car_keywords = [
        "price",
        "cost",
        "spec",
        "specs",
        "feature",
        "engine",
        "fuel",
        "seat",
        "suv",
        "sedan",
        "pickup",
        "mpv",
        "hybrid",
        "diesel",
        "gasoline",
        "ev",
        "preowned",
        "pre-owned",
        "used",
        "mileage",
        "compare",
        "recommend",
        "budget",
        "warranty",
        "service",
    ]
    if any(k in t for k in car_keywords):
        return False

    off_topic = ["joke", "song", "movie", "weather", "love", "dating", "translate", "math", "game"]
    return any(k in t for k in off_topic)


def _is_service_company_rag_intent(user_text: str) -> bool:
    t = _low(user_text)

    if re.search(r"\b(service|services|serviced|servicing|maintenance|repair|appointment|book|booking|schedule)\b", t):
        return True
    if re.search(r"\b(branch|branches|showroom|dealer|dealership|service center|workshop|contact|hotline|phone|address|location)\b", t):
        return True
    if re.search(r"\b(company profile|profile|history|mission|vision|official distributor|distributor)\b", t):
        return True
    if re.search(r"\b(toyota plus|genuine parts|parts policy|warranty|guarantee|coverage)\b", t):
        return True
    if re.search(r"\bservice\s*[a-d]\b.*\b(price|cost)\b", t):
        return True
    if re.search(r"\b(certified\s+pre.?owned|cpo|pre.?owned\s+program|preowned\s+program)\b", t):
        return True
    if re.search(r"\bhow\s+(often|frequently|long)\b", t) and re.search(r"\b(service|serviced|maintenance|maintain)\b", t):
        return True
    if re.search(r"\b(provide|provides|offer|offers)\b", t) and "toyota" in t:
        return True

    return False


def chat_turn(
    user_text: str,
    state: Dict[str, Any],
    full_rows: List[Dict[str, Any]],
    rag_engine: Any,
    preowned_engine: PreownedEngine,
    debug: bool = False,
) -> Dict[str, Any]:

    if not state:
        _reset_state(state)

    user_text = _clean(user_text)
    if not user_text:
        return _sys("Please type a question.")

    user_text = _resolve_with_history(user_text, state, full_rows)
    t0 = _low(user_text)

    if t0 in {"/reset", "reset"}:
        _reset_state(state)
        return _sys("Reset done.")

    if _is_small_talk(user_text):
        if t0 in {"thanks", "thank you", "ty"}:
            return _sys("You're welcome. What would you like to know about Toyota Cambodia?")
        if t0 in {"bye", "goodbye"}:
            return _sys("Bye. If you need anything about Toyota models, price, specs, or services, just ask.")
        return _sys(_welcome_text())

    if _is_gibberish(user_text):
        return _sys(
            "Please ask a Toyota vehicle question such as price, specs, features, comparison, recommendation, "
            "pre-owned listings, warranty, or service information."
        )

    if _is_off_topic(user_text, full_rows):
        return _sys(
            "I can only help with Toyota Cambodia vehicle information such as price, specs, features, "
            "comparison, recommendation, pre-owned listings, warranty, or service information."
        )

    if _is_not_answerable(user_text):
        return _sys(
            "I don't have that information in our dataset. "
            "Please ask about Toyota models, price, specs, features, comparison, recommendations, or services."
        )

    if _is_general_knowledge_question(user_text, full_rows) and getattr(rag_engine, "available", False):
        out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
        out["text"] = _remove_markdown_bold(style_answer(user_text, out, DEFAULT_STYLE))
        return _pipe(out, "RAG")

    if (_is_warranty_or_services_info_question(user_text) or _is_service_company_rag_intent(user_text)) and getattr(rag_engine, "available", False):
        out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
        out["text"] = _remove_markdown_bold(out.get("text") or "")
        return _pipe(out, "RAG")

    if is_preowned_intent(user_text) and _looks_like_preowned_listing_query(user_text):
        _cancel_reco_flow(state)

        result = preowned_engine.query(user_text, top_k=10)
        ans = preowned_engine.format_answer(result)

        text = str(ans.get("text") or "").strip()
        sources = ans.get("sources") or []

        if not text:
            if sources:
                lines = ["Here are Toyota Certified Pre-Owned listings:"]
                for i, s in enumerate(sources[:10], start=1):
                    lines.append(f"{i}. {s}")
                text = "\n".join(lines)
            else:
                text = "Sorry, I couldn't find any pre-owned listings."

        res = {"answer_type": "preowned", "text": text, "facts": [text], "sources": sources}
        styled = style_answer(user_text, res, DEFAULT_STYLE)
        if styled and styled.strip():
            res["text"] = styled
        return _pipe(res, "PREOWNED_RAG")

    mentioned = detect_model_in_text(user_text, full_rows)
    if mentioned:
        state["last_model"] = mentioned

    if _is_compare_intent(user_text):
        models = _extract_compare_models(user_text, full_rows)

        if len(models) >= 2:
            _cancel_reco_flow(state)
            return _pipe(_do_compare(full_rows, models[0], models[1]), "CSV_METHOD")

        msg = "Which two Toyota models do you want to compare? Example: compare Veloz vs Vios"
        return _pipe({"answer_type": "csv_compare", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

    if is_spec_intent(user_text):
        unk = _unknown_model_if_any(user_text, full_rows)
        if unk:
            msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
            return _pipe({"answer_type": "csv_specs", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

        model = detect_model_in_text(user_text, full_rows) or state.get("last_model")
        if not model:
            return _sys("Which model are you asking about?")

        state["last_model"] = model
        _cancel_reco_flow(state)
        return _pipe(answer_specs_from_csv(full_rows, model), "CSV_METHOD")

    if is_summary_intent(user_text):
        unk = _unknown_model_if_any(user_text, full_rows)
        if unk:
            msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
            return _pipe({"answer_type": "csv_summary", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

        model = detect_model_in_text(user_text, full_rows) or state.get("last_model")
        if not model:
            return _sys("Which model are you asking about?")

        state["last_model"] = model
        _cancel_reco_flow(state)
        return _pipe(answer_summary_from_csv(full_rows, model), "CSV_METHOD")

    if any(k in t0 for k in ["price", "how much", "cost", "starting price"]):
        if any(k in t0 for k in ["under", "below", "budget", "less than"]):
            pass
        else:
            unk = _unknown_model_if_any(user_text, full_rows)
            if unk:
                msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
                return _pipe({"answer_type": "csv_price", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

            model = resolve_target_model(user_text, state.get("last_model"), full_rows)
            if not model:
                msg = "Which Toyota model price do you want?"
                return _pipe({"answer_type": "csv_price", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

            state["last_model"] = model
            _cancel_reco_flow(state)
            return _pipe(answer_price_from_csv(full_rows, model), "CSV_METHOD")

    is_reco = (
        is_recommendation_intent(user_text)
        or state.get("slot_fill_active") is True
        or _looks_like_filter(user_text, full_rows)
    )

    if is_reco:
        b = extract_budget(user_text)
        s = extract_seats(user_text)
        f = extract_fuel(user_text)
        bt = extract_body_type(user_text)

        if b is not None:
            state["slots"]["max_budget"] = b
        if s is not None:
            state["slots"]["min_seats"] = s
        if f:
            state["slots"]["fuel"] = f
        if bt:
            state["slots"]["body_type"] = bt

        missing = _missing_slots(state["slots"])
        if missing:
            state["slot_fill_active"] = True
            if "budget" in missing:
                return _csv_msg("Tell me your budget (USD). Example: budget 40000")
            if "body" in missing:
                return _csv_msg("What body type do you want? (SUV / Sedan / Pickup / MPV / Bus)")
            if "fuel" in missing:
                return _csv_msg("What fuel do you prefer? (Gasoline / Diesel / Hybrid / EV)")
            return _csv_msg("Please provide: " + ", ".join(missing))

        max_budget = float(state["slots"]["max_budget"])
        min_seats = int(state["slots"]["min_seats"] or 0)
        fuel = state["slots"]["fuel"]
        body_type = state["slots"]["body_type"]

        verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
        res = build_reco_answer(verified, possible, max_items=5)
        _cancel_reco_flow(state)
        return _pipe(res, "CSV_METHOD")

    feature_key = detect_feature_key(user_text)
    if feature_key:
        unk = _unknown_model_if_any(user_text, full_rows)
        if unk:
            msg = f"I couldn't find {unk.title()} in the Toyota Cambodia dataset."
            return _pipe({"answer_type": "csv_feature", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

        model = resolve_target_model(user_text, state.get("last_model"), full_rows)
        if not model:
            msg = "Which Toyota model are you asking about?"
            return _pipe({"answer_type": "csv_feature", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

        state["last_model"] = model
        _cancel_reco_flow(state)

        res = answer_feature_from_csv(full_rows, model, feature_key)
        if res:
            return _pipe(res, "CSV_METHOD")

        msg = "That feature is not available in the dataset yet."
        return _pipe({"answer_type": "csv_feature", "text": msg, "facts": [msg], "sources": []}, "CSV_METHOD")

    if getattr(rag_engine, "available", False):
        out = rag_engine.rag_answer(user_text, last_model_norm=state.get("last_model"))
        out["text"] = _remove_markdown_bold(out.get("text") or "")
        styled = _remove_markdown_bold(style_answer(user_text, out, DEFAULT_STYLE))
        if styled and styled.strip():
            out["text"] = styled
        return _pipe(out, "RAG")

    return _unknown_question_response(user_text, state)


def render_answer(
    user_text: str,
    res: Dict[str, Any],
    use_llm: bool = False,
    rewrite_csv: bool = False,
    debug: bool = False,
) -> str:
    text = str(res.get("answer") or res.get("text") or "").strip()
    if not text:
        facts = res.get("facts") or []
        if isinstance(facts, list) and facts:
            text = str(facts[0]).strip()
    if not text:
        text = "Sorry — I couldn't produce an answer."

    text = _remove_markdown_bold(text)

    sources = [s for s in (res.get("sources") or []) if s]

    pipeline = str(res.get("pipeline") or "")
    is_rag = pipeline == "RAG" or str(res.get("answer_type") or "").lower() == "rag"
    is_csv = pipeline == "CSV_METHOD"

    if use_llm and is_rag:
        text = llm_rewrite(user_text, text, res.get("facts") or [text], sources)
    elif rewrite_csv and is_csv:
        text = llm_rewrite(user_text, text, res.get("facts") or [text], sources)

    if sources:
        text += "\nSources: " + ", ".join(sources[:3])

    if debug and res.get("pipeline"):
        text += f"\n[PIPELINE={res['pipeline']}]"

    if debug and res.get("pipeline") == "RAG" and res.get("evidence"):
        ev = res.get("evidence") or []
        lines = []
        for e in ev[:5]:
            lines.append(f"- chunk={e.get('chunk_id')} score={e.get('score')} url={e.get('source_url')}")
        if lines:
            text += "\nEVIDENCE:\n" + "\n".join(lines)

    return text