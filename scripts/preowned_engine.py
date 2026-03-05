# # # from __future__ import annotations
# # #
# # # from dataclasses import dataclass
# # # from pathlib import Path
# # # from typing import List, Optional, Dict, Any
# # #
# # # import pandas as pd
# # # import re
# # #
# # #
# # # @dataclass
# # # class PreownedResult:
# # #     rows: pd.DataFrame
# # #     sources: List[str]
# # #
# # #
# # # class PreownedEngine:
# # #     def __init__(self, csv_path: Path):
# # #         self.csv_path = Path(csv_path)
# # #         self.df: Optional[pd.DataFrame] = None
# # #
# # #     @classmethod
# # #     def load_from_csv(cls, csv_path: Path) -> "PreownedEngine":
# # #         eng = cls(Path(csv_path))
# # #         eng.load()
# # #         return eng
# # #
# # #     def load(self) -> None:
# # #         if not self.csv_path.exists():
# # #             raise FileNotFoundError(f"Preowned CSV not found: {self.csv_path}")
# # #
# # #         df = pd.read_csv(self.csv_path)
# # #
# # #         required = {"model", "price_usd", "year", "mileage_km", "plate_no"}
# # #         missing = required - set(df.columns)
# # #         if missing:
# # #             raise ValueError(f"Missing required columns in preowned CSV: {sorted(missing)}")
# # #
# # #         if "source_url" not in df.columns:
# # #             df["source_url"] = ""
# # #         if "location" not in df.columns:
# # #             df["location"] = ""
# # #
# # #         df["model_norm"] = df["model"].astype(str).str.lower().str.strip()
# # #         df["plate_norm"] = df["plate_no"].astype(str).str.lower().str.strip()
# # #
# # #         for c in ["price_usd", "year", "mileage_km"]:
# # #             df[c] = pd.to_numeric(df[c], errors="coerce")
# # #
# # #         df = df.dropna(subset=["price_usd", "year", "mileage_km", "model", "plate_no"])
# # #
# # #         self.df = df
# # #
# # #     def _extract_plate(self, text: str) -> Optional[str]:
# # #         t = text.lower()
# # #         m = re.search(r"\b([a-z]{1,5}-\d{1,4}[a-z]{0,2}-\d{2,5})\b", t)
# # #         if m:
# # #             return m.group(1)
# # #         m = re.search(r"\b([a-z]{1,5}-\d{2,6})\b", t)
# # #         if m:
# # #             return m.group(1)
# # #         return None
# # #
# # #     def _extract_year(self, text: str) -> Optional[int]:
# # #         m = re.search(r"\b(19\d{2}|20\d{2})\b", text)
# # #         if not m:
# # #             return None
# # #         y = int(m.group(1))
# # #         if 1990 <= y <= 2035:
# # #             return y
# # #         return None
# # #
# # #     def _extract_price(self, text: str) -> Optional[float]:
# # #         t = text.lower().replace(",", "")
# # #         m = re.search(r"\b(\d{4,6})\s*(usd|\$)?\b", t)
# # #         if not m:
# # #             return None
# # #         try:
# # #             return float(m.group(1))
# # #         except Exception:
# # #             return None
# # #
# # #     def _extract_mileage(self, text: str) -> Optional[float]:
# # #         t = text.lower().replace(",", "")
# # #         m = re.search(r"\b(\d{1,3}(?:\.\d+)?)\s*(k|km)\b", t)
# # #         if m:
# # #             val = float(m.group(1))
# # #             unit = m.group(2)
# # #             if unit == "k":
# # #                 return val * 1000.0
# # #             return val
# # #         m = re.search(r"\b(\d{4,7})\s*km\b", t)
# # #         if m:
# # #             return float(m.group(1))
# # #         return None
# # #
# # #     def query(self, user_text: str, top_k: int = 10) -> PreownedResult:
# # #         if self.df is None:
# # #             self.load()
# # #
# # #         q = user_text.strip().lower()
# # #         df = self.df
# # #
# # #         plate = self._extract_plate(q)
# # #         if plate:
# # #             hits = df[df["plate_norm"].str.contains(plate, na=False)]
# # #             hits = hits.sort_values(["year", "mileage_km"], ascending=[False, True]).head(top_k)
# # #             return PreownedResult(hits, hits["source_url"].dropna().unique().tolist())
# # #
# # #         year = self._extract_year(q)
# # #         price = self._extract_price(q)
# # #         mileage = self._extract_mileage(q)
# # #
# # #         model_words = [w for w in re.split(r"[^a-z0-9]+", q) if w]
# # #         model_hits = df[df["model_norm"].apply(lambda m: any(w in m for w in model_words))]
# # #
# # #         hits = model_hits if not model_hits.empty else df.copy()
# # #
# # #         if year is not None:
# # #             hits = hits[hits["year"] == year]
# # #
# # #         if price is not None:
# # #             if any(k in q for k in ["under", "below", "max", "<="]):
# # #                 hits = hits[hits["price_usd"] <= price]
# # #             elif any(k in q for k in ["over", "above", "min", ">="]):
# # #                 hits = hits[hits["price_usd"] >= price]
# # #
# # #         if mileage is not None:
# # #             if any(k in q for k in ["under", "below", "max", "<="]):
# # #                 hits = hits[hits["mileage_km"] <= mileage]
# # #             elif any(k in q for k in ["over", "above", "min", ">="]):
# # #                 hits = hits[hits["mileage_km"] >= mileage]
# # #
# # #         hits = hits.sort_values(["year", "mileage_km"], ascending=[False, True]).head(top_k)
# # #
# # #         return PreownedResult(hits, hits["source_url"].dropna().unique().tolist())
# # #
# # #     def format_answer(self, result: PreownedResult) -> Dict[str, Any]:
# # #         if result.rows is None or result.rows.empty:
# # #             return {
# # #                 "answer": "No matching pre-owned listings found. Try: 'Fortuner preowned', 'Veloz preowned', or include plate like 'PP-2CB-7465'.",
# # #                 "pipeline": "PREOWNED_RAG",
# # #                 "sources": [],
# # #             }
# # #
# # #         lines = []
# # #         for _, r in result.rows.iterrows():
# # #             price_txt = "N/A"
# # #             try:
# # #                 price_txt = f"${int(float(r['price_usd'])):,}"
# # #             except Exception:
# # #                 pass
# # #
# # #             year_txt = "N/A"
# # #             try:
# # #                 year_txt = str(int(float(r["year"])))
# # #             except Exception:
# # #                 pass
# # #
# # #             km_txt = "N/A"
# # #             try:
# # #                 km_txt = f"{int(float(r['mileage_km'])):,} km"
# # #             except Exception:
# # #                 pass
# # #
# # #             plate_txt = str(r.get("plate_no") or "N/A")
# # #             loc_txt = str(r.get("location") or "N/A")
# # #
# # #             lines.append(
# # #                 f"- {r['model']} | Plate: {plate_txt} | Location: {loc_txt} | Year: {year_txt} | Mileage: {km_txt} | Price: {price_txt}"
# # #             )
# # #
# # #         return {
# # #             "answer": "Here are matching pre-owned listings:\n" + "\n".join(lines),
# # #             "pipeline": "PREOWNED_RAG",
# # #             "sources": result.sources,
# # #         }
# #
# # """
# # preowned_engine.py  –  Pre-owned listing search for the Toyota chatbot.
# #
# # PATH RESOLUTION ORDER for preowned_master.csv:
# #   1. Explicit path passed to PreownedEngine(csv_path=...)
# #   2. <project_root>/preowned_master.csv
# #   3. <project_root>/data_preowned/csv_preowned/preowned_master.csv
# #   4. <project_root>/data/preowned_master.csv
# #   5. scripts/preowned_master.csv
# #   6. One level above project_root
# # """
# # from __future__ import annotations
# #
# # import csv
# # import re
# # from pathlib import Path
# # from typing import Any, Dict, List, Optional, Tuple
# #
# # _SCRIPTS_DIR  = Path(__file__).resolve().parent
# # _PROJECT_ROOT = _SCRIPTS_DIR.parent
# #
# #
# # def _find_preowned_csv(override: Optional[str] = None) -> Optional[Path]:
# #     """Search everywhere and return first match for preowned_master.csv, or None."""
# #     filename = "preowned_master.csv"
# #
# #     if override:
# #         p = Path(override).expanduser().resolve()
# #         if p.exists():
# #             return p
# #
# #     fixed = [
# #         _PROJECT_ROOT / filename,
# #         _PROJECT_ROOT / "data_preowned" / "csv_preowned" / filename,
# #         _PROJECT_ROOT / "data_preowned" / filename,
# #         _PROJECT_ROOT / "data" / filename,
# #         _PROJECT_ROOT / "data_new" / filename,
# #         _SCRIPTS_DIR / filename,
# #         _PROJECT_ROOT.parent / filename,
# #         _PROJECT_ROOT.parent / "data" / filename,
# #     ]
# #     for p in fixed:
# #         if p.exists():
# #             return p
# #
# #     # Recursive glob — finds the file no matter which subfolder it is in
# #     for p in _PROJECT_ROOT.rglob(filename):
# #         return p
# #
# #     for p in _PROJECT_ROOT.parent.rglob(filename):
# #         return p
# #
# #     return None
# #
# #
# # # ---------------------------------------------------------------------------
# # # Intent detection
# # # ---------------------------------------------------------------------------
# #
# # def is_preowned_intent(text: str) -> bool:
# #     t = (text or "").lower()
# #     # Explicit signals
# #     signals = [
# #         "preowned", "pre-owned", "pre owned",
# #         "second hand", "secondhand", "second-hand", "2nd hand",
# #         "certified pre-owned", "cpo",
# #         "listing", "listings",
# #         "mileage", " km",
# #         "plate", "license plate", "number plate",
# #     ]
# #     if any(s in t for s in signals):
# #         return True
# #     # "used" only if it comes at the start or as a standalone modifier
# #     if re.search(r"\bused\b", t):
# #         return True
# #     return False
# #
# #
# # # ---------------------------------------------------------------------------
# # # Slot extraction (preowned-specific)
# # # ---------------------------------------------------------------------------
# #
# # def _extract_budget(text: str) -> Optional[float]:
# #     t = (text or "").lower().replace(",", "")
# #     m = re.search(r"(?:under|below|max|budget|<)\s*\$?\s*(\d{4,6}(?:\.\d+)?)", t)
# #     if m:
# #         try:
# #             return float(m.group(1))
# #         except Exception:
# #             pass
# #     return None
# #
# #
# # def _extract_year(text: str) -> Optional[int]:
# #     m = re.search(r"\b(19\d{2}|20\d{2})\b", text or "")
# #     if m:
# #         y = int(m.group(1))
# #         if 1990 <= y <= 2035:
# #             return y
# #     return None
# #
# #
# # def _extract_mileage_max(text: str) -> Optional[float]:
# #     t = (text or "").lower().replace(",", "")
# #     m = re.search(r"(?:under|below|max|less than)\s+(\d{1,6})\s*km", t)
# #     if m:
# #         return float(m.group(1))
# #     return None
# #
# #
# # def _extract_plate(text: str) -> Optional[str]:
# #     t = (text or "").lower()
# #     # e.g. "PP-2CB-7465"
# #     m = re.search(r"([a-z]{1,4}[-\s]\d[a-z]{1,3}[-\s]\d{3,5})", t)
# #     if m:
# #         return m.group(1).replace(" ", "-")
# #     # e.g. "PP-2345"
# #     m2 = re.search(r"([a-z]{1,4}[-]\d{2,6})", t)
# #     if m2:
# #         return m2.group(1)
# #     return None
# #
# #
# # # ---------------------------------------------------------------------------
# # # PreownedEngine
# # # ---------------------------------------------------------------------------
# #
# # class PreownedEngine:
# #     def __init__(self, csv_path: Optional[str] = None):
# #         """
# #         Args:
# #             csv_path: Optional explicit path to preowned_master.csv.
# #                       Auto-searched if omitted.
# #         """
# #         resolved = _find_preowned_csv(override=csv_path)
# #         if resolved:
# #             self.csv_path: Optional[Path] = resolved
# #             print(f"[preowned_engine] preowned CSV: {resolved}")
# #         else:
# #             # Store None — queries will return empty, not crash
# #             self.csv_path = None
# #             tried = csv_path or str(_PROJECT_ROOT / "preowned_master.csv")
# #             print(
# #                 f"[preowned_engine] WARNING: preowned_master.csv not found "
# #                 f"(searched from {tried}). Pre-owned queries will return no results."
# #             )
# #         self._rows: Optional[List[Dict[str, Any]]] = None
# #
# #     # ------------------------------------------------------------------
# #     def _load(self) -> List[Dict[str, Any]]:
# #         if self._rows is not None:
# #             return self._rows
# #         if not self.csv_path or not self.csv_path.exists():
# #             self._rows = []
# #             return self._rows
# #
# #         with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
# #             rows = [dict(r) for r in csv.DictReader(f)]
# #
# #         for r in rows:
# #             for col in ("price_usd", "year", "mileage_km"):
# #                 try:
# #                     r[col] = float(str(r.get(col, "") or "").replace(",", "").strip())
# #                 except Exception:
# #                     r[col] = None
# #             r["_model_norm"] = (r.get("model") or "").lower().strip()
# #             r["_plate_norm"] = (r.get("plate_no") or "").lower().strip()
# #
# #         self._rows = rows
# #         return self._rows
# #
# #     # ------------------------------------------------------------------
# #     def _match_model(self, rows: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
# #         """Filter rows where any query word (>2 chars) appears in the model name."""
# #         words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if len(w) > 2]
# #         # Exclude common stop words that appear in many model names
# #         stop = {"the", "for", "are", "have", "has", "its", "with", "and", "that", "this"}
# #         words = [w for w in words if w not in stop]
# #         if not words:
# #             return rows
# #         matched = [r for r in rows if any(w in r["_model_norm"] for w in words)]
# #         return matched if matched else rows
# #
# #     # ------------------------------------------------------------------
# #     def query(self, user_text: str, top_k: int = 10) -> Dict[str, Any]:
# #         rows = self._load()
# #         if not rows:
# #             return {"rows": [], "sources": []}
# #
# #         q = (user_text or "").strip()
# #
# #         # Plate exact search
# #         plate = _extract_plate(q)
# #         if plate:
# #             hits = [r for r in rows if plate in r["_plate_norm"]]
# #             hits.sort(key=lambda r: (-(r["year"] or 0), r["mileage_km"] or 1e9))
# #             return {"rows": hits[:top_k], "sources": _collect_sources(hits[:top_k])}
# #
# #         # Model filter
# #         hits = self._match_model(rows, q)
# #
# #         # Year filter
# #         year = _extract_year(q)
# #         if year is not None:
# #             hits = [r for r in hits if r.get("year") == year]
# #
# #         # Mileage cap
# #         max_km = _extract_mileage_max(q)
# #         if max_km is not None:
# #             hits = [r for r in hits if r.get("mileage_km") is not None and r["mileage_km"] <= max_km]
# #
# #         # Budget cap
# #         budget = _extract_budget(q)
# #         if budget is not None:
# #             hits = [r for r in hits if r.get("price_usd") is not None and r["price_usd"] <= budget]
# #
# #         hits.sort(key=lambda r: (-(r["year"] or 0), r["mileage_km"] or 1e9))
# #         return {"rows": hits[:top_k], "sources": _collect_sources(hits[:top_k])}
# #
# #     # ------------------------------------------------------------------
# #     def format_answer(self, result: Dict[str, Any]) -> Dict[str, Any]:
# #         rows    = result.get("rows") or []
# #         sources = result.get("sources") or []
# #
# #         if not rows:
# #             return {
# #                 "text": (
# #                     "No matching pre-owned listings found. "
# #                     "Try: 'Fortuner Legender preowned', 'Veloz preowned price', "
# #                     "or search with a plate like 'PP-2CB-7465'."
# #                 ),
# #                 "sources": [],
# #                 "pipeline": "PREOWNED_RAG",
# #             }
# #
# #         prices   = [r["price_usd"]  for r in rows if r.get("price_usd")  is not None]
# #         years    = [r["year"]        for r in rows if r.get("year")        is not None]
# #         mileages = [r["mileage_km"]  for r in rows if r.get("mileage_km") is not None]
# #
# #         summary: List[str] = []
# #         if prices:
# #             summary.append(f"Price range: ${min(prices):,.0f} – ${max(prices):,.0f}")
# #         if years:
# #             summary.append(f"Year range: {int(min(years))} – {int(max(years))}")
# #         if mileages:
# #             summary.append(f"Mileage range: {int(min(mileages)):,} – {int(max(mileages)):,} km")
# #
# #         lines: List[str] = []
# #         for r in rows[:10]:
# #             model = (r.get("model") or "N/A").strip()
# #             price = f"${r['price_usd']:,.0f}" if r.get("price_usd") is not None else "N/A"
# #             year  = str(int(r["year"])) if r.get("year") is not None else "N/A"
# #             km    = f"{int(r['mileage_km']):,} km" if r.get("mileage_km") is not None else "N/A"
# #             plate = (r.get("plate_no") or "N/A").strip()
# #             fuel  = (r.get("fuel") or "N/A").strip()
# #             trans = (r.get("transmission") or "N/A").strip()
# #             lines.append(
# #                 f"- {model} | Plate: {plate} | Year: {year} | Mileage: {km} "
# #                 f"| Price: {price} | Fuel: {fuel} | Trans: {trans}"
# #             )
# #
# #         text = "Pre-owned listings found:\n"
# #         if summary:
# #             text += "Summary: " + " | ".join(summary) + "\n"
# #         text += "\n".join(lines)
# #
# #         return {"text": text, "sources": sources, "pipeline": "PREOWNED_RAG"}
# #
# #
# # # ---------------------------------------------------------------------------
# # # Helpers
# # # ---------------------------------------------------------------------------
# #
# # def _collect_sources(rows: List[Dict[str, Any]]) -> List[str]:
# #     seen: set = set()
# #     out: List[str] = []
# #     for r in rows:
# #         u = (r.get("source_url") or "").strip()
# #         if u and u not in seen:
# #             seen.add(u)
# #             out.append(u)
# #     return out
#
# """
# preowned_engine.py  –  Pre-owned listing search for the Toyota chatbot.
#
# PATH RESOLUTION ORDER for preowned_master.csv:
#   1. Explicit path passed to PreownedEngine(csv_path=...)
#   2. <project_root>/preowned_master.csv
#   3. <project_root>/data_preowned/csv_preowned/preowned_master.csv
#   4. <project_root>/data/preowned_master.csv
#   5. scripts/preowned_master.csv
#   6. One level above project_root
# """
# from __future__ import annotations
#
# import csv
# import re
# from pathlib import Path
# from typing import Any, Dict, List, Optional, Tuple
#
# _SCRIPTS_DIR  = Path(__file__).resolve().parent
# _PROJECT_ROOT = _SCRIPTS_DIR.parent
#
#
# def _find_preowned_csv(override: Optional[str] = None) -> Optional[Path]:
#     """Search everywhere and return first match for preowned_master.csv, or None."""
#     filename = "preowned_master.csv"
#
#     if override:
#         p = Path(override).expanduser().resolve()
#         if p.exists():
#             return p
#
#     fixed = [
#         _PROJECT_ROOT / filename,
#         _PROJECT_ROOT / "data_preowned" / "csv_preowned" / filename,
#         _PROJECT_ROOT / "data_preowned" / filename,
#         _PROJECT_ROOT / "data" / filename,
#         _PROJECT_ROOT / "data_new" / filename,
#         _SCRIPTS_DIR / filename,
#         _PROJECT_ROOT.parent / filename,
#         _PROJECT_ROOT.parent / "data" / filename,
#     ]
#     for p in fixed:
#         if p.exists():
#             return p
#
#     # Recursive glob — finds the file no matter which subfolder it is in
#     for p in _PROJECT_ROOT.rglob(filename):
#         return p
#
#     for p in _PROJECT_ROOT.parent.rglob(filename):
#         return p
#
#     return None
#
#
# # ---------------------------------------------------------------------------
# # Intent detection
# # ---------------------------------------------------------------------------
#
# def is_preowned_intent(text: str) -> bool:
#     t = (text or "").lower()
#     # Explicit signals
#     signals = [
#         "preowned", "pre-owned", "pre owned",
#         "second hand", "secondhand", "second-hand", "2nd hand",
#         "certified pre-owned", "cpo",
#         "listing", "listings",
#         "mileage", " km",
#         "plate", "license plate", "number plate",
#     ]
#     if any(s in t for s in signals):
#         return True
#     # "used" only if it comes at the start or as a standalone modifier
#     if re.search(r"\bused\b", t):
#         return True
#     return False
#
#
# # ---------------------------------------------------------------------------
# # Slot extraction (preowned-specific)
# # ---------------------------------------------------------------------------
#
# def _extract_budget(text: str) -> Optional[float]:
#     t = (text or "").lower().replace(",", "")
#     m = re.search(r"(?:under|below|max|budget|<)\s*\$?\s*(\d{4,6}(?:\.\d+)?)", t)
#     if m:
#         try:
#             return float(m.group(1))
#         except Exception:
#             pass
#     return None
#
#
# def _extract_year(text: str) -> Optional[int]:
#     m = re.search(r"\b(19\d{2}|20\d{2})\b", text or "")
#     if m:
#         y = int(m.group(1))
#         if 1990 <= y <= 2035:
#             return y
#     return None
#
#
# def _extract_mileage_max(text: str) -> Optional[float]:
#     t = (text or "").lower().replace(",", "")
#     m = re.search(r"(?:under|below|max|less than)\s+(\d{1,6})\s*km", t)
#     if m:
#         return float(m.group(1))
#     return None
#
#
# def _extract_plate(text: str) -> Optional[str]:
#     t = (text or "").lower()
#     # e.g. "PP-2CB-7465"
#     m = re.search(r"([a-z]{1,4}[-\s]\d[a-z]{1,3}[-\s]\d{3,5})", t)
#     if m:
#         return m.group(1).replace(" ", "-")
#     # e.g. "PP-2345"
#     m2 = re.search(r"([a-z]{1,4}[-]\d{2,6})", t)
#     if m2:
#         return m2.group(1)
#     return None
#
#
# # ---------------------------------------------------------------------------
# # PreownedEngine
# # ---------------------------------------------------------------------------
#
# class PreownedEngine:
#     def __init__(self, csv_path: Optional[str] = None):
#         """
#         Args:
#             csv_path: Optional explicit path to preowned_master.csv.
#                       Auto-searched if omitted.
#         """
#         resolved = _find_preowned_csv(override=csv_path)
#         if resolved:
#             self.csv_path: Optional[Path] = resolved
#             print(f"[preowned_engine] preowned CSV: {resolved}")
#         else:
#             # Store None — queries will return empty, not crash
#             self.csv_path = None
#             tried = csv_path or str(_PROJECT_ROOT / "preowned_master.csv")
#             print(
#                 f"[preowned_engine] WARNING: preowned_master.csv not found "
#                 f"(searched from {tried}). Pre-owned queries will return no results."
#             )
#         self._rows: Optional[List[Dict[str, Any]]] = None
#
#     # ------------------------------------------------------------------
#     def _load(self) -> List[Dict[str, Any]]:
#         if self._rows is not None:
#             return self._rows
#         if not self.csv_path or not self.csv_path.exists():
#             self._rows = []
#             return self._rows
#
#         with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
#             rows = [dict(r) for r in csv.DictReader(f)]
#
#         for r in rows:
#             for col in ("price_usd", "year", "mileage_km"):
#                 try:
#                     r[col] = float(str(r.get(col, "") or "").replace(",", "").strip())
#                 except Exception:
#                     r[col] = None
#             r["_model_norm"] = (r.get("model") or "").lower().strip()
#             r["_plate_norm"] = (r.get("plate_no") or "").lower().strip()
#
#         self._rows = rows
#         return self._rows
#
#     # ------------------------------------------------------------------
#     def _match_model(self, rows: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
#         """Filter rows where any query word (>2 chars) appears in the model name."""
#         words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if len(w) > 2]
#         # Exclude common stop words that appear in many model names
#         stop = {"the", "for", "are", "have", "has", "its", "with", "and", "that", "this"}
#         words = [w for w in words if w not in stop]
#         if not words:
#             return rows
#         matched = [r for r in rows if any(w in r["_model_norm"] for w in words)]
#         return matched if matched else rows
#
#     # ------------------------------------------------------------------
#     def query(self, user_text: str, top_k: int = 10) -> Dict[str, Any]:
#         rows = self._load()
#         if not rows:
#             return {"rows": [], "sources": []}
#
#         q = (user_text or "").strip()
#
#         # Plate exact search
#         plate = _extract_plate(q)
#         if plate:
#             hits = [r for r in rows if plate in r["_plate_norm"]]
#             hits.sort(key=lambda r: (-(r["year"] or 0), r["mileage_km"] or 1e9))
#             return {"rows": hits[:top_k], "sources": _collect_sources(hits[:top_k])}
#
#         # Model filter
#         hits = self._match_model(rows, q)
#
#         # Year filter
#         year = _extract_year(q)
#         if year is not None:
#             hits = [r for r in hits if r.get("year") == year]
#
#         # Mileage cap
#         max_km = _extract_mileage_max(q)
#         if max_km is not None:
#             hits = [r for r in hits if r.get("mileage_km") is not None and r["mileage_km"] <= max_km]
#
#         # Budget cap
#         budget = _extract_budget(q)
#         if budget is not None:
#             hits = [r for r in hits if r.get("price_usd") is not None and r["price_usd"] <= budget]
#
#         hits.sort(key=lambda r: (-(r["year"] or 0), r["mileage_km"] or 1e9))
#         return {"rows": hits[:top_k], "sources": _collect_sources(hits[:top_k])}
#
#     # ------------------------------------------------------------------
#     def format_answer(self, result: Dict[str, Any]) -> Dict[str, Any]:
#         rows    = result.get("rows") or []
#         sources = result.get("sources") or []
#
#         if not rows:
#             return {
#                 "text": (
#                     "Sorry, I couldn't find any pre-owned listings matching your request. "
#                     "Try searching by model name (e.g. *Fortuner Legender preowned*), "
#                     "by price (e.g. *Veloz preowned under $35000*), "
#                     "or by plate number (e.g. *PP-2CB-7465*). I'm happy to help! 😊"
#                 ),
#                 "sources": [],
#                 "pipeline": "PREOWNED_RAG",
#             }
#
#         prices   = [r["price_usd"]  for r in rows if r.get("price_usd")  is not None]
#         years    = [r["year"]        for r in rows if r.get("year")        is not None]
#         mileages = [r["mileage_km"]  for r in rows if r.get("mileage_km") is not None]
#
#         count = len(rows[:10])
#         text = f"I found **{count} pre-owned listing{'s' if count != 1 else ''}** for you:\n\n"
#
#         if prices and years and mileages:
#             text += (
#                 f"📊 **Overview:** "
#                 f"Price ${min(prices):,.0f}–${max(prices):,.0f} | "
#                 f"Year {int(min(years))}–{int(max(years))} | "
#                 f"Mileage {int(min(mileages)):,}–{int(max(mileages)):,} km\n\n"
#             )
#
#         for i, r in enumerate(rows[:10], 1):
#             model = (r.get("model") or "N/A").strip()
#             price = f"${r['price_usd']:,.0f}" if r.get("price_usd") is not None else "N/A"
#             year  = str(int(r["year"])) if r.get("year") is not None else "N/A"
#             km    = f"{int(r['mileage_km']):,} km" if r.get("mileage_km") is not None else "N/A"
#             plate = (r.get("plate_no") or "N/A").strip()
#             fuel  = (r.get("fuel") or "N/A").title()
#             trans = (r.get("transmission") or "N/A").strip()
#             text += (
#                 f"{i}. **{model}** ({year})\n"
#                 f"   💰 {price}  |  📍 {plate}  |  🛣️ {km}\n"
#                 f"   ⛽ {fuel}  |  ⚙️ {trans}\n\n"
#             )
#
#         text += "Would you like more details on any of these listings? 😊"
#         return {"text": text, "sources": sources, "pipeline": "PREOWNED_RAG"}
#
#
# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------
#
# def _collect_sources(rows: List[Dict[str, Any]]) -> List[str]:
#     seen: set = set()
#     out: List[str] = []
#     for r in rows:
#         u = (r.get("source_url") or "").strip()
#         if u and u not in seen:
#             seen.add(u)
#             out.append(u)
#     return out

"""
preowned_engine.py  –  Pre-owned listing search for the Toyota chatbot.

PATH RESOLUTION ORDER for preowned_master.csv:
  1. Explicit path passed to PreownedEngine(csv_path=...)
  2. <project_root>/preowned_master.csv
  3. <project_root>/data_preowned/csv_preowned/preowned_master.csv
  4. <project_root>/data/preowned_master.csv
  5. scripts/preowned_master.csv
  6. One level above project_root
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent


def _find_preowned_csv(override: Optional[str] = None) -> Optional[Path]:
    filename = "preowned_master.csv"

    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return p

    fixed = [
        _PROJECT_ROOT / filename,
        _PROJECT_ROOT / "data_preowned" / "csv_preowned" / filename,
        _PROJECT_ROOT / "data_preowned" / filename,
        _PROJECT_ROOT / "data" / filename,
        _PROJECT_ROOT / "data_new" / filename,
        _SCRIPTS_DIR / filename,
        _PROJECT_ROOT.parent / filename,
        _PROJECT_ROOT.parent / "data" / filename,
    ]
    for p in fixed:
        if p.exists():
            return p

    for p in _PROJECT_ROOT.rglob(filename):
        return p
    for p in _PROJECT_ROOT.parent.rglob(filename):
        return p
    return None


def _low(s: Any) -> str:
    return (str(s) or "").strip().lower()


def _norm_token(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

def is_preowned_intent(text: str) -> bool:
    t = (text or "").lower()
    signals = [
        "preowned", "pre-owned", "pre owned",
        "second hand", "secondhand", "second-hand", "2nd hand",
        "certified pre-owned", "cpo",
        "listing", "listings",
        "mileage", " km",
        "plate", "license plate", "number plate",
        "used",
    ]
    return any(s in t for s in signals)


# ---------------------------------------------------------------------------
# Slot extraction (preowned-specific)
# ---------------------------------------------------------------------------

def _extract_budget(text: str) -> Optional[float]:
    t = (text or "").lower().replace(",", "")
    m = re.search(r"(?:under|below|max|budget|<|less\s+than)\s*\$?\s*(\d{4,6}(?:\.\d+)?)", t)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


def _extract_year(text: str) -> Optional[int]:
    m = re.search(r"\b(19\d{2}|20\d{2})\b", text or "")
    if m:
        y = int(m.group(1))
        if 1990 <= y <= 2035:
            return y
    return None


def _extract_mileage_max(text: str) -> Optional[float]:
    t = (text or "").lower().replace(",", "")
    m = re.search(r"(?:under|below|max|less\s+than)\s+(\d{1,6})\s*km", t)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


def _extract_plate(text: str) -> Optional[str]:
    t = (text or "").lower()
    m = re.search(r"([a-z]{1,4}[-\s]\d[a-z]{1,3}[-\s]\d{3,5})", t)
    if m:
        return m.group(1).replace(" ", "-")
    m2 = re.search(r"([a-z]{1,4}[-]\d{2,6})", t)
    if m2:
        return m2.group(1)
    return None


def _extract_fuel(text: str) -> Optional[str]:
    t = _low(text)
    if "diesel" in t:
        return "diesel"
    if "gasoline" in t or re.search(r"\bgas\b", t):
        return "gasoline"
    if "hybrid" in t or "hev" in t:
        return "hybrid"
    if "ev" in t or "electric" in t:
        return "ev"
    return None


def _extract_body_type(text: str) -> Optional[str]:
    t = _low(text)
    if "pickup" in t or "pick-up" in t or "pick up" in t or "truck" in t:
        return "pickup"
    if "suv" in t:
        return "suv"
    if "sedan" in t:
        return "sedan"
    if "mpv" in t:
        return "mpv"
    if "bus" in t:
        return "bus"
    return None


# ---------------------------------------------------------------------------
# Query parsing helpers
# ---------------------------------------------------------------------------

# Words that should NOT be treated as model words
_STOP = {
    "pre", "owned", "preowned", "pre-owned", "used", "cpo", "certified",
    "listing", "listings", "under", "below", "less", "than", "max", "budget",
    "price", "year", "mileage", "km", "plate", "number",
    "suv", "sedan", "mpv", "pickup", "truck", "bus",
    "diesel", "gasoline", "gas", "hybrid", "hev", "ev", "electric",
    "toyota", "for", "show", "me", "find",
}

# Basic Toyota model keywords (enough for your dataset)
_MODEL_HINTS = {
    "raize", "rush", "veloz", "yaris", "corolla", "fortuner",
    "hilux", "hiace", "land", "cruiser", "vios", "wigo",
}


def _extract_model_words(query: str) -> List[str]:
    words = [w for w in re.split(r"[^a-z0-9]+", (query or "").lower()) if len(w) > 2]
    words = [w for w in words if w not in _STOP]
    return words


def _looks_like_model_query(query: str) -> bool:
    t = _low(query)
    # If any model hint appears, treat it as a model query
    return any(h in t for h in _MODEL_HINTS)


def _match_model(rows: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    If user likely named a model: filter by model words.
    If user did NOT name a model (only filters like suv/diesel/budget): return all rows.
    If user named a model but no match: return empty (do not fallback to all).
    """
    if not _looks_like_model_query(query):
        return rows

    words = _extract_model_words(query)
    if not words:
        return rows

    matched = [r for r in rows if any(w in r["_model_norm"] for w in words)]
    return matched  # may be empty on purpose


def _fuel_matches(requested: Optional[str], row_fuel: str) -> bool:
    if not requested:
        return True
    rf = _norm_token(row_fuel)
    if requested == "diesel":
        return "diesel" in rf
    if requested == "gasoline":
        return "gasoline" in rf or rf == "gas"
    if requested == "hybrid":
        return "hybrid" in rf or "hev" in rf
    if requested == "ev":
        return "ev" in rf or "electric" in rf
    return True


def _body_matches(requested: Optional[str], row_body: str) -> bool:
    if not requested:
        return True
    rb = _norm_token(row_body)
    # Normalize some common variants
    if "pick" in rb or "truck" in rb:
        rb = "pickup"
    if "sport utility" in rb:
        rb = "suv"
    return requested in rb


# ---------------------------------------------------------------------------
# PreownedEngine
# ---------------------------------------------------------------------------

class PreownedEngine:
    def __init__(self, csv_path: Optional[str] = None):
        resolved = _find_preowned_csv(override=csv_path)
        if resolved:
            self.csv_path: Optional[Path] = resolved
            print(f"[preowned_engine] preowned CSV: {resolved}")
        else:
            self.csv_path = None
            tried = csv_path or str(_PROJECT_ROOT / "preowned_master.csv")
            print(
                f"[preowned_engine] WARNING: preowned_master.csv not found "
                f"(searched from {tried}). Pre-owned queries will return no results."
            )
        self._rows: Optional[List[Dict[str, Any]]] = None

    def _load(self) -> List[Dict[str, Any]]:
        if self._rows is not None:
            return self._rows
        if not self.csv_path or not self.csv_path.exists():
            self._rows = []
            return self._rows

        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            rows = [dict(r) for r in csv.DictReader(f)]

        for r in rows:
            for col in ("price_usd", "year", "mileage_km"):
                try:
                    r[col] = float(str(r.get(col, "") or "").replace(",", "").strip())
                except Exception:
                    r[col] = None

            r["_model_norm"] = _norm_token(r.get("model") or "")
            r["_plate_norm"] = _norm_token(r.get("plate_no") or "")
            r["_fuel_norm"] = _norm_token(r.get("fuel") or "")
            r["_body_norm"] = _norm_token(r.get("body_type") or "")

        self._rows = rows
        return self._rows

    def query(self, user_text: str, top_k: int = 10) -> Dict[str, Any]:
        rows = self._load()
        if not rows:
            return {"rows": [], "sources": []}

        q = (user_text or "").strip()

        # Plate exact search
        plate = _extract_plate(q)
        if plate:
            hits = [r for r in rows if plate.lower() in r["_plate_norm"]]
            hits.sort(key=lambda r: (-(r["year"] or 0), r["mileage_km"] or 1e9))
            return {"rows": hits[:top_k], "sources": _collect_sources(hits[:top_k])}

        # Parse filters
        budget = _extract_budget(q)
        year = _extract_year(q)
        max_km = _extract_mileage_max(q)
        fuel = _extract_fuel(q)
        body = _extract_body_type(q)

        # Model filter (only if user actually mentioned a model)
        hits = _match_model(rows, q)

        # Apply filters
        if year is not None:
            hits = [r for r in hits if r.get("year") == year]

        if max_km is not None:
            hits = [r for r in hits if r.get("mileage_km") is not None and r["mileage_km"] <= max_km]

        if budget is not None:
            hits = [r for r in hits if r.get("price_usd") is not None and r["price_usd"] <= budget]

        if fuel is not None:
            hits = [r for r in hits if _fuel_matches(fuel, r.get("fuel") or "")]

        if body is not None:
            hits = [r for r in hits if _body_matches(body, r.get("body_type") or "")]

        hits.sort(key=lambda r: (-(r["year"] or 0), r["mileage_km"] or 1e9))
        return {"rows": hits[:top_k], "sources": _collect_sources(hits[:top_k])}

    def format_answer(self, result: Dict[str, Any]) -> Dict[str, Any]:
        rows = result.get("rows") or []
        sources = result.get("sources") or []

        if not rows:
            return {
                "text": (
                    "Sorry, I couldn't find any pre-owned listings matching your request.\n"
                    "Try:\n"
                    "- model name (e.g. Fortuner Legender preowned)\n"
                    "- filter (e.g. pre-owned SUV under $35000 gasoline)\n"
                    "- plate number (e.g. PP-2CB-7465)"
                ),
                "sources": [],
                "pipeline": "PREOWNED_RAG",
            }

        prices = [r["price_usd"] for r in rows if r.get("price_usd") is not None]
        years = [r["year"] for r in rows if r.get("year") is not None]
        mileages = [r["mileage_km"] for r in rows if r.get("mileage_km") is not None]

        count = len(rows[:10])
        text = f"I found **{count} pre-owned listing{'s' if count != 1 else ''}**:\n\n"

        if prices and years and mileages:
            text += (
                f"Overview: "
                f"Price ${min(prices):,.0f}–${max(prices):,.0f} | "
                f"Year {int(min(years))}–{int(max(years))} | "
                f"Mileage {int(min(mileages)):,}–{int(max(mileages)):,} km\n\n"
            )

        for i, r in enumerate(rows[:10], 1):
            model = (r.get("model") or "N/A").strip()
            price = f"${r['price_usd']:,.0f}" if r.get("price_usd") is not None else "N/A"
            year = str(int(r["year"])) if r.get("year") is not None else "N/A"
            km = f"{int(r['mileage_km']):,} km" if r.get("mileage_km") is not None else "N/A"
            plate = (r.get("plate_no") or "N/A").strip()
            fuel = (r.get("fuel") or "N/A").strip()
            trans = (r.get("transmission") or "N/A").strip()
            body = (r.get("body_type") or "N/A").strip()

            text += (
                f"{i}. {model} ({year})\n"
                f"   Price: {price} | Plate: {plate} | Mileage: {km}\n"
                f"   Fuel: {fuel} | Transmission: {trans} | Body: {body}\n\n"
            )

        text += "Reply with a listing number (1–10) or plate number to see more details."
        return {"text": text, "sources": sources, "pipeline": "PREOWNED_RAG"}


def _collect_sources(rows: List[Dict[str, Any]]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for r in rows:
        u = (r.get("source_url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out