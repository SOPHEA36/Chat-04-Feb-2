# # scripts/csv_engine.py
# import csv
# import re
# import difflib
# from pathlib import Path
# from typing import Dict, Any, List, Optional, Tuple
#
# # ==========================================================
# # PATHS
# # ==========================================================
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# CSV_FULL = PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv"
#
# # ==========================================================
# # CONSTANTS
# # ==========================================================
# FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}
# BODY_TYPES = {"suv", "sedan", "pickup", "bus", "mpv", "mvp", "van", "any"}
#
# # ==========================================================
# # FEATURE MAP
# # ==========================================================
# FEATURE_MAP: Dict[str, Dict[str, Any]] = {
#     "pvm": {
#         "aliases": ["pvm", "panoramic view monitor", "panoramic view", "around view monitor"],
#         "columns": ["spec_panoramic_view_monitor_pvm"],
#         "label": "Panoramic View Monitor (PVM)",
#     },
#     "camera_360": {
#         "aliases": [
#             "360 camera",
#             "camera 360",
#             "360-degree camera",
#             "360° camera",
#             "surround view camera",
#             "surround-view camera",
#             "birds eye camera",
#             "bird view camera",
#         ],
#         "columns": [],
#         "label": "360° surround-view camera",
#     },
#     "reverse_camera": {
#         "aliases": ["reverse camera", "rear camera", "backup camera", "reversing camera"],
#         "columns": ["spec_reverse_camera"],
#         "label": "Reverse camera",
#     },
#     "adaptive_cruise": {
#         "aliases": ["adaptive cruise", "acc", "drcc", "radar cruise", "dynamic radar cruise", "cruise control"],
#         "columns": [
#             "spec_fullspeed_range_adaptive_cruise_control_acc",
#             "spec_dynamic_radar_cruise_control_drcc",
#             "spec_cruise_control",
#         ],
#         "label": "Cruise control",
#     },
#     "bsm": {
#         "aliases": ["blind spot", "bsm", "blind spot monitor"],
#         "columns": ["spec_blind_spot_monitor_bsm"],
#         "label": "Blind Spot Monitor (BSM)",
#     },
#     "carplay_android": {
#         "aliases": ["carplay", "apple carplay", "android auto"],
#         "columns": ["spec_apple_carplay_and_android_auto", "spec_apple_carplay_or_android_auto"],
#         "label": "Apple CarPlay / Android Auto",
#     },
#     "turning_radius": {
#         "aliases": [
#             "turning radius",
#             "minimum turning radius",
#             "min turning radius",
#             "turning circle",
#             "minimum turning circle",
#         ],
#         "columns": ["spec_minimum_turning_radius_tire"],
#         "label": "Minimum turning radius",
#     },
#     "price": {
#         "aliases": ["price", "cost", "how much", "usd"],
#         "columns": ["price_usd"],
#         "label": "Price (USD)",
#     },
# }
#
# # ==========================================================
# # CSV LOAD
# # ==========================================================
# def load_csv(path: Path) -> List[Dict[str, Any]]:
#     with path.open("r", encoding="utf-8", newline="") as f:
#         return list(csv.DictReader(f))
#
#
# def load_full_rows() -> List[Dict[str, Any]]:
#     return load_csv(CSV_FULL)
#
# # ==========================================================
# # NORMALIZATION HELPERS
# # ==========================================================
# def normalize_model_name(s: str) -> str:
#     return re.sub(r"\s+", " ", (s or "").lower().strip())
#
#
# def _compact(s: str) -> str:
#     return re.sub(r"[^a-z0-9]", "", (s or "").lower())
#
#
# def to_int(v: Any) -> Optional[int]:
#     try:
#         if v is None:
#             return None
#         s = str(v).strip()
#         if not s:
#             return None
#         s = s.replace(",", "")
#         return int(float(s))
#     except Exception:
#         return None
#
#
# def _squeeze_repeats(text: str) -> str:
#     return re.sub(r"(.)\1{2,}", r"\1\1", text)
#
#
# def _normalize_text(text: str) -> str:
#     t = (text or "").lower()
#     t = _squeeze_repeats(t)
#
#     t = re.sub(r"\bseadan\b", "sedan", t)
#     t = re.sub(r"\bsaloon\b", "sedan", t)
#     t = re.sub(r"\bmpvs?\b", "mpv", t)
#     t = re.sub(r"\bmvp\b", "mpv", t)
#     t = re.sub(r"\bmini\s*van\b", "van", t)
#     t = re.sub(r"\bpick[\s\-]?up\b", "pickup", t)
#     t = re.sub(r"\bvan\b", "bus", t)
#
#     t = re.sub(r"\bdisel\b", "diesel", t)
#     t = re.sub(r"\bdissel\b", "diesel", t)
#     t = re.sub(r"\bgazoline\b", "gasoline", t)
#     t = re.sub(r"\bgasolin\b", "gasoline", t)
#     t = re.sub(r"\bpetrol\b", "gasoline", t)
#     t = re.sub(r"\bhybird\b", "hybrid", t)
#     t = re.sub(r"\bhev\b", "hybrid", t)
#
#     return t
#
#
# def _tokenize(text: str) -> List[str]:
#     t = _normalize_text(text)
#     t = re.sub(r"[^a-z0-9]+", " ", t)
#     t = re.sub(r"\s+", " ", t).strip()
#     return t.split()
#
# # ==========================================================
# # FUZZY HELPERS
# # ==========================================================
# def _extract_after_of_phrase(text: str) -> Optional[str]:
#     t = _normalize_text(text)
#     m = re.search(r"\bof\s+([a-z0-9\s\-]+)$", t)
#     if not m:
#         return None
#     phrase = (m.group(1) or "").strip()
#     return phrase if phrase else None
#
#
# def _is_explicit_model_query(text: str) -> bool:
#     t = _normalize_text(text)
#     return bool(re.search(r"\bof\s+[a-z0-9]", t))
#
#
# def _best_fuzzy_model_match(user_text: str, full_rows: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
#     t = _normalize_text(user_text)
#     t_comp = _compact(t)
#     if not t_comp:
#         return None, 0.0
#
#     best_model = None
#     best_score = 0.0
#
#     for r in full_rows:
#         model_raw = str(r.get("model") or "")
#         model_norm = normalize_model_name(model_raw)
#         if not model_norm:
#             continue
#
#         m_comp = _compact(model_norm)
#         if not m_comp:
#             continue
#
#         score = difflib.SequenceMatcher(None, t_comp, m_comp).ratio()
#         if score > best_score:
#             best_score = score
#             best_model = model_norm
#
#     return best_model, best_score
#
# # ==========================================================
# # MODEL MATCHING
# # ==========================================================
# def detect_model_in_text(text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
#     t_norm = normalize_model_name(_normalize_text(text))
#     t_comp = _compact(t_norm)
#     t_tokens = set(t_norm.split())
#
#     best = None
#     best_overlap = 0
#
#     for r in full_rows:
#         model_raw = str(r.get("model") or "")
#         model_norm = normalize_model_name(model_raw)
#         if not model_norm:
#             continue
#
#         if model_norm in t_norm:
#             return model_norm
#
#         m_comp = _compact(model_norm)
#         if m_comp and m_comp in t_comp:
#             return model_norm
#
#         m_tokens = set(model_norm.split())
#         overlap = len(m_tokens.intersection(t_tokens))
#         if overlap >= 2 and overlap > best_overlap:
#             best_overlap = overlap
#             best = model_norm
#
#     phrase = _extract_after_of_phrase(text)
#     if phrase:
#         fuzzy_best, fuzzy_score = _best_fuzzy_model_match(phrase, full_rows)
#         if fuzzy_best and fuzzy_score >= 0.78:
#             return fuzzy_best
#
#     fuzzy_best, fuzzy_score = _best_fuzzy_model_match(text, full_rows)
#     if fuzzy_best and fuzzy_score >= 0.82:
#         return fuzzy_best
#
#     return best
#
#
# def prefer_last_model_if_close(mentioned_model_norm: Optional[str], last_model_norm: Optional[str]) -> Optional[str]:
#     if not mentioned_model_norm:
#         return None
#     if not last_model_norm:
#         return mentioned_model_norm
#     if mentioned_model_norm in last_model_norm:
#         return last_model_norm
#     return mentioned_model_norm
#
#
# def resolve_target_model(user_text: str, last_model: Optional[str], full_rows: List[Dict[str, Any]]) -> Optional[str]:
#     mentioned = detect_model_in_text(user_text, full_rows)
#     if mentioned:
#         return prefer_last_model_if_close(mentioned, last_model)
#
#     t = _normalize_text(user_text)
#
#     if t.startswith(("how about", "what about")):
#         rest = re.sub(r"^(how about|what about)\s+", "", t).strip()
#         mentioned2 = detect_model_in_text(rest, full_rows)
#         if mentioned2:
#             return prefer_last_model_if_close(mentioned2, last_model)
#         return None
#
#     if _is_explicit_model_query(t):
#         return None
#
#     if any(p in t for p in ["it", "this model", "that model", "this one", "the car"]):
#         return last_model
#
#     return last_model
#
# # ==========================================================
# # FEATURE DETECTION
# # ==========================================================
# def detect_feature_key(text: str) -> Optional[str]:
#     t = _normalize_text(text)
#     for key, meta in FEATURE_MAP.items():
#         for alias in meta.get("aliases", []):
#             if alias in t:
#                 return key
#     return None
#
# # ==========================================================
# # YES/NO PARSING
# # ==========================================================
# def yn_from_value(val: Any) -> Optional[bool]:
#     if val is None:
#         return None
#
#     s = str(val).strip().lower()
#     if not s:
#         return None
#
#     s = s.replace("_", " ").replace("-", " ")
#     s = re.sub(r"\s+", " ", s)
#
#     yes_values = {"yes", "true", "1", "available", "standard", "included", "present"}
#     no_values = {"no", "false", "0", "not available", "na", "n/a", "none", "absent"}
#
#     if s in yes_values or s.startswith("standard") or s.startswith("included"):
#         return True
#     if s in no_values or s.startswith("not"):
#         return False
#
#     return None
#
# # ==========================================================
# # CSV FEATURE ANSWERING
# # ==========================================================
# def find_row_by_model(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
#     for r in full_rows:
#         if normalize_model_name(r.get("model")) == model_norm:
#             return r
#     return None
#
#
# def answer_feature_from_csv(full_rows: List[Dict[str, Any]], model_norm: str, feature_key: str) -> Optional[Dict[str, Any]]:
#     row = find_row_by_model(full_rows, model_norm)
#     if not row:
#         return None
#
#     model_name = row.get("model") or "This model"
#     src = row.get("url") or ""
#
#     meta = FEATURE_MAP.get(feature_key)
#     if not meta:
#         return None
#
#     for col in meta["columns"]:
#         val = row.get(col)
#         if val in (None, ""):
#             continue
#
#         if feature_key == "price":
#             price = to_int(val)
#             if price is None:
#                 value = str(val).strip()
#                 text = f"{model_name} — Price (USD): {value}"
#             else:
#                 value = f"${price}"
#                 text = f"{model_name} — Price (USD): {value}"
#             return {
#                 "answer_type": "csv_feature",
#                 "text": text,
#                 "value": value,
#                 "facts": [text],
#                 "sources": [src] if src else [],
#                 "model": model_name,
#                 "feature": feature_key,
#             }
#
#         yn = yn_from_value(val)
#         if yn is True:
#             value = "Yes"
#             text = f"Yes — {model_name} has {meta['label']} according to official specifications."
#         elif yn is False:
#             value = "No"
#             text = f"No — {model_name} does not list {meta['label']} in the official specifications."
#         else:
#             value = str(val).strip()
#             if feature_key == "turning_radius":
#                 text = f"{model_name} — {meta['label']}: {value}"
#             else:
#                 text = f"{model_name}: {meta['label']} = {value}"
#
#         return {
#             "answer_type": "csv_feature",
#             "text": text,
#             "value": value,
#             "facts": [text],
#             "sources": [src] if src else [],
#             "model": model_name,
#             "feature": feature_key,
#         }
#
#     if feature_key == "camera_360":
#         value = "No"
#         text = f"No — {model_name} does not list {FEATURE_MAP['camera_360']['label']} in the official specifications we captured."
#         return {
#             "answer_type": "csv_feature",
#             "text": text,
#             "value": value,
#             "facts": [text],
#             "sources": [src] if src else [],
#             "model": model_name,
#             "feature": feature_key,
#         }
#
#     return None
#
# # ==========================================================
# # RECOMMENDATION INTENT + EXTRACTORS
# # ==========================================================
# def is_recommendation_intent(text: str) -> bool:
#     t = _normalize_text(text)
#
#     if re.search(r"\b(spec|specs|specification|details)\b", t):
#         return False
#
#     if extract_budget(t) is not None:
#         return True
#     if extract_seats(t) is not None:
#         return True
#     if extract_fuel(t) is not None:
#         return True
#     if extract_body_type(t) is not None:
#         return True
#
#     if any(k in t for k in ["recommend", "suggest", "buy", "looking for", "need a car", "budget"]):
#         return True
#
#     return False
#
#
# def extract_budget(text: str) -> Optional[int]:
#     m = re.search(r"\$?\s*([\d,]{4,})", text or "", flags=re.IGNORECASE)
#     if not m:
#         return None
#     n = m.group(1).replace(",", "")
#     return int(n) if n.isdigit() else None
#
#
# def extract_seats(text: str) -> Optional[int]:
#     m = re.search(r"(\d+)\s*(?:seat|seats|seater)\b", text or "", flags=re.IGNORECASE)
#     return int(m.group(1)) if m else None
#
#
# def extract_fuel(text: str) -> Optional[str]:
#     tokens = set(_tokenize(text))
#     if "diesel" in tokens:
#         return "diesel"
#     if "gasoline" in tokens:
#         return "gasoline"
#     if "hybrid" in tokens:
#         return "hybrid"
#     if "ev" in tokens or "electric" in tokens:
#         return "ev"
#     if "any" in tokens:
#         return "any"
#     return None
#
#
# def extract_body_type(text: str) -> Optional[str]:
#     tokens = set(_tokenize(text))
#     if "sedan" in tokens:
#         return "sedan"
#     if "suv" in tokens:
#         return "suv"
#     if "pickup" in tokens:
#         return "pickup"
#     if "bus" in tokens:
#         return "bus"
#     if "mpv" in tokens:
#         return "mpv"
#     if "any" in tokens:
#         return "any"
#     return None
#
# # ==========================================================
# # RECOMMENDATION FILTERING
# # ==========================================================
# def _seats_value(row: Dict[str, Any]) -> Optional[int]:
#     v = to_int(row.get("seats"))
#     if v is not None:
#         return v
#     return to_int(row.get("spec_seating_capacity"))
#
#
# def filter_cars_split(
#     rows: List[Dict[str, Any]],
#     max_budget: int,
#     min_seats: int,
#     fuel: str,
#     body_type: str,
# ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
#     fuel = (fuel or "any").lower().strip()
#     body_type = (body_type or "any").lower().strip()
#
#     verified: List[Dict[str, Any]] = []
#     possible: List[Dict[str, Any]] = []
#
#     for r in rows:
#         price = to_int(r.get("price_usd"))
#         if price is None or price > max_budget:
#             continue
#
#         row_fuel = (r.get("fuel") or "").lower().strip()
#         row_body = (r.get("body_type") or "").lower().strip()
#
#         if fuel != "any" and row_fuel != fuel:
#             continue
#         if body_type != "any" and row_body != body_type:
#             continue
#
#         seats_val = _seats_value(r)
#         if seats_val is None:
#             possible.append(r)
#             continue
#         if seats_val < min_seats:
#             continue
#
#         verified.append(r)
#
#     verified.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
#     possible.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
#     return verified, possible
#
#
# def build_reco_answer(
#     verified: List[Dict[str, Any]],
#     possible: List[Dict[str, Any]],
#     max_items: int = 5,
# ) -> Dict[str, Any]:
#     if not verified and not possible:
#         return {
#             "answer_type": "csv_reco",
#             "text": "I couldn't find an official match with those constraints. Try increasing budget, lowering seats, changing body type, or using fuel = Any.",
#             "facts": [],
#             "sources": [],
#         }
#
#     lines: List[str] = []
#     sources: List[str] = []
#
#     if verified:
#         lines.append("Based on your requirements, here are official matches:\n")
#         for m in verified[:max_items]:
#             brand = m.get("brand", "")
#             model = m.get("model", "")
#             price = m.get("price_usd", "")
#             seats_val = _seats_value(m)
#             seats_txt = str(seats_val) if seats_val is not None else "N/A"
#             f = m.get("fuel", "")
#             body = m.get("body_type", "")
#             url = m.get("url", "")
#
#             lines.append(f"- {brand} {model} (${price}), seats={seats_txt}, fuel={f}, body={body}")
#             if url:
#                 sources.append(url)
#
#     if possible:
#         if lines:
#             lines.append("")
#         lines.append("Possible matches (some required fields are N/A in CSV):\n")
#         for m in possible[:max_items]:
#             brand = m.get("brand", "")
#             model = m.get("model", "")
#             price = m.get("price_usd", "")
#             seats_val = _seats_value(m)
#             seats_txt = str(seats_val) if seats_val is not None else "N/A"
#             f = m.get("fuel", "")
#             body = m.get("body_type", "")
#             url = m.get("url", "")
#
#             lines.append(f"- {brand} {model} (${price}), seats={seats_txt}, fuel={f}, body={body}")
#             if url:
#                 sources.append(url)
#
#     return {"answer_type": "csv_reco", "text": "\n".join(lines).strip(), "facts": [], "sources": sources}
#
# # ==========================================================
# # SUMMARY INTENT (SAFETY)
# # ==========================================================
# def is_summary_intent(text: str) -> bool:
#     t = _normalize_text(text)
#     keys = [
#         "safety system", "safety systems", "safety feature", "safety features",
#         "safety", "adas", "driver assist", "driver assistance", "toyota safety sense", "tss",
#     ]
#     return any(k in t for k in keys)
#
#
# def _yn_label(val: Any) -> str:
#     yn = yn_from_value(val)
#     if yn is True:
#         return "Yes"
#     if yn is False:
#         return "No"
#     s = str(val).strip() if val is not None else ""
#     return s if s else "N/A"
#
#
# def _build_safety_summary(row: Dict[str, Any]) -> List[str]:
#     lines: List[str] = []
#
#     def add(label: str, col: str):
#         v = row.get(col)
#         if v not in (None, ""):
#             lines.append(f"- {label}: {_yn_label(v)}")
#
#     add("ABS", "spec_antilock_braking_system_abs")
#     add("Vehicle Stability Control (VSC)", "spec_vehicle_stability_control_vsc")
#     add("SRS Airbags", "spec_srs_airbags")
#     add("Blind Spot Monitor (BSM)", "spec_blind_spot_monitor_bsm")
#     add("Lane Departure Warning (LDW)", "spec_lane_departure_warning_ldw")
#     add("Lane Keeping Control (LKC)", "spec_lane_keeping_control_lkc")
#     add("Pre-Collision Warning (PCW)", "spec_precollision_warning_pcw")
#     add("Pre-Collision Braking (PCB)", "spec_precollision_braking_pcb")
#     add("Reverse camera", "spec_reverse_camera")
#     add("Panoramic View Monitor (PVM)", "spec_panoramic_view_monitor_pvm")
#
#     sr = str(row.get("spec_safety_rating") or "").strip()
#     if sr:
#         lines.append(f"- Safety rating: {sr}")
#
#     return lines
#
#
# def answer_summary_from_csv(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
#     row = find_row_by_model(full_rows, model_norm)
#     if not row:
#         return None
#
#     model_name = row.get("model") or "This model"
#     src = row.get("url") or ""
#
#     lines = _build_safety_summary(row)
#     if not lines:
#         text = f"I couldn't find structured safety fields for {model_name} in the CSV."
#     else:
#         text = f"{model_name} — Safety systems (from official CSV):\n" + "\n".join(lines)
#
#     return {
#         "answer_type": "csv_summary",
#         "text": text,
#         "facts": [text],
#         "sources": [src] if src else [],
#         "model": model_name,
#         "summary_type": "safety",
#     }

# Good enough
# # scripts/csv_engine.py
# import csv
# import re
# import difflib
# from pathlib import Path
# from typing import Dict, Any, List, Optional, Tuple
#
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# CSV_FULL = PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv"
#
# FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}
# BODY_TYPES = {"suv", "sedan", "pickup", "bus", "mpv", "mvp", "van", "hatchback", "any"}
#
# MODEL_STOP_TOKENS = {
#     "hev", "hybrid", "electric", "ev",
#     "gasoline", "diesel",
#     "mt", "at", "manual", "automatic", "transmission",
#     "edition", "legender", "rally", "gr", "gr-s", "zx", "vx", "vxr",
#     "seater", "seaters",
# }
#
# # Alias map (typos / nicknames -> official model)
# # Key and values are normalized (lower, single spaces).
# MODEL_ALIASES: Dict[str, str] = {
#     "vigo": "wigo",
#     "viggo": "wigo",
#     "wiggo": "wigo",
# }
#
# FEATURE_MAP: Dict[str, Dict[str, Any]] = {
#     "pvm": {
#         "aliases": ["pvm", "panoramic view monitor", "panoramic view", "around view monitor"],
#         "columns": ["spec_panoramic_view_monitor_pvm"],
#         "label": "Panoramic View Monitor (PVM)",
#     },
#     "camera_360": {
#         "aliases": [
#             "360 camera", "camera 360", "360-degree camera", "360° camera",
#             "surround view camera", "surround-view camera",
#             "birds eye camera", "bird view camera",
#         ],
#         "columns": [],
#         "label": "360° surround-view camera",
#     },
#     "reverse_camera": {
#         "aliases": ["reverse camera", "rear camera", "backup camera", "reversing camera"],
#         "columns": ["spec_reverse_camera"],
#         "label": "Reverse camera",
#     },
#     "adaptive_cruise": {
#         "aliases": ["adaptive cruise", "acc", "drcc", "radar cruise", "dynamic radar cruise", "cruise control"],
#         "columns": [
#             "spec_fullspeed_range_adaptive_cruise_control_acc",
#             "spec_dynamic_radar_cruise_control_drcc",
#             "spec_cruise_control",
#         ],
#         "label": "Cruise control",
#     },
#     "bsm": {
#         "aliases": ["blind spot", "bsm", "blind spot monitor"],
#         "columns": ["spec_blind_spot_monitor_bsm"],
#         "label": "Blind Spot Monitor (BSM)",
#     },
#     "carplay_android": {
#         "aliases": ["carplay", "apple carplay", "android auto"],
#         "columns": ["spec_apple_carplay_and_android_auto", "spec_apple_carplay_or_android_auto"],
#         "label": "Apple CarPlay / Android Auto",
#     },
#     "turning_radius": {
#         "aliases": [
#             "turning radius", "minimum turning radius", "min turning radius",
#             "turning circle", "minimum turning circle",
#         ],
#         "columns": ["spec_minimum_turning_radius_tire"],
#         "label": "Minimum turning radius",
#     },
#     "wireless_charging": {
#         "aliases": ["wireless charging", "wireless charger", "qi", "charging pad"],
#         "columns": ["spec_wireless_charging", "Wireless charging"],
#         "label": "Wireless charging",
#     },
#     "ambient_lighting": {
#         "aliases": ["ambient lighting", "ambient light", "mood lighting"],
#         "columns": ["spec_ambient_lighting", "Ambient lighting"],
#         "label": "Ambient lighting",
#     },
#     "price": {
#         "aliases": ["price", "cost", "how much", "selling price", "usd", "$"],
#         "columns": ["price_usd"],
#         "label": "Price (USD)",
#     },
# }
#
# def load_csv(path: Path) -> List[Dict[str, Any]]:
#     with path.open("r", encoding="utf-8", newline="") as f:
#         return list(csv.DictReader(f))
#
# def load_full_rows() -> List[Dict[str, Any]]:
#     return load_csv(CSV_FULL)
#
# def normalize_model_name(s: str) -> str:
#     return re.sub(r"\s+", " ", (s or "").lower().strip())
#
# def _compact(s: str) -> str:
#     return re.sub(r"[^a-z0-9]", "", (s or "").lower())
#
# def to_int(v: Any) -> Optional[int]:
#     try:
#         if v is None:
#             return None
#         s = str(v).strip()
#         if not s:
#             return None
#         s = s.replace(",", "")
#         return int(float(s))
#     except Exception:
#         return None
#
# def format_price_usd(v: Any) -> str:
#     n = to_int(v)
#     if n is None:
#         s = str(v).strip() if v is not None else ""
#         return s if s else "N/A"
#     return f"${n:,}"
#
# def _squeeze_repeats(text: str) -> str:
#     return re.sub(r"(.)\1{2,}", r"\1\1", text)
#
# def _normalize_text(text: str) -> str:
#     t = (text or "").lower()
#     t = _squeeze_repeats(t)
#
#     t = re.sub(r"\bseadan\b", "sedan", t)
#     t = re.sub(r"\bsaloon\b", "sedan", t)
#     t = re.sub(r"\bmpvs?\b", "mpv", t)
#     t = re.sub(r"\bmvp\b", "mpv", t)
#     t = re.sub(r"\bmini\s*van\b", "van", t)
#     t = re.sub(r"\bpick[\s\-]?up\b", "pickup", t)
#     t = re.sub(r"\bvan\b", "bus", t)
#
#     t = re.sub(r"\bdisel\b", "diesel", t)
#     t = re.sub(r"\bdissel\b", "diesel", t)
#     t = re.sub(r"\bgazoline\b", "gasoline", t)
#     t = re.sub(r"\bgasolin\b", "gasoline", t)
#     t = re.sub(r"\bpetrol\b", "gasoline", t)
#     t = re.sub(r"\bhybird\b", "hybrid", t)
#     t = re.sub(r"\bhev\b", "hybrid", t)
#
#     return t
#
# def _tokenize(text: str) -> List[str]:
#     t = _normalize_text(text)
#     t = re.sub(r"[^a-z0-9]+", " ", t)
#     t = re.sub(r"\s+", " ", t).strip()
#     return t.split()
#
# def _model_tokens(model_norm: str) -> List[str]:
#     return [t for t in re.split(r"\s+", (model_norm or "").strip()) if t]
#
# def _base_model_tokens(model_norm: str) -> List[str]:
#     toks = _model_tokens(model_norm)
#     base = [t for t in toks if t not in MODEL_STOP_TOKENS]
#     return base if base else toks
#
# def _extract_after_of_phrase(text: str) -> Optional[str]:
#     t = _normalize_text(text)
#     m = re.search(r"\bof\s+([a-z0-9\s\-]+)$", t)
#     if not m:
#         return None
#     phrase = (m.group(1) or "").strip()
#     return phrase if phrase else None
#
# def _best_fuzzy_model_match(user_text: str, full_rows: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
#     t = _normalize_text(user_text)
#     t_comp = _compact(t)
#     if not t_comp:
#         return None, 0.0
#
#     best_model = None
#     best_score = 0.0
#
#     for r in full_rows:
#         model_norm = normalize_model_name(str(r.get("model") or ""))
#         if not model_norm:
#             continue
#         m_comp = _compact(model_norm)
#         if not m_comp:
#             continue
#         score = difflib.SequenceMatcher(None, t_comp, m_comp).ratio()
#         if score > best_score:
#             best_score = score
#             best_model = model_norm
#
#     return best_model, best_score
#
# def find_row_by_model(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
#     for r in full_rows:
#         if normalize_model_name(r.get("model")) == model_norm:
#             return r
#     return None
#
# def _row_fuel(row: Dict[str, Any]) -> str:
#     return (row.get("fuel") or "").strip().lower()
#
# def _pick_best_variant(
#     candidates: List[Tuple[str, Dict[str, Any]]],
#     user_fuel_pref: Optional[str],
# ) -> Optional[str]:
#     if not candidates:
#         return None
#
#     if user_fuel_pref and user_fuel_pref in FUELS and user_fuel_pref != "any":
#         filtered = [c for c in candidates if _row_fuel(c[1]) == user_fuel_pref]
#         if filtered:
#             candidates = filtered
#
#     candidates_sorted = sorted(
#         candidates,
#         key=lambda x: (to_int(x[1].get("price_usd")) if to_int(x[1].get("price_usd")) is not None else 10**12)
#     )
#     return candidates_sorted[0][0]
#
# def extract_budget(text: str) -> Optional[int]:
#     m = re.search(r"\$?\s*([\d,]{4,})", text or "", flags=re.IGNORECASE)
#     if not m:
#         return None
#     n = m.group(1).replace(",", "")
#     return int(n) if n.isdigit() else None
#
# def extract_seats(text: str) -> Optional[int]:
#     m = re.search(r"(\d+)\s*(?:seat|seats|seater)\b", text or "", flags=re.IGNORECASE)
#     return int(m.group(1)) if m else None
#
# def extract_fuel(text: str) -> Optional[str]:
#     tokens = set(_tokenize(text))
#     if "diesel" in tokens:
#         return "diesel"
#     if "gasoline" in tokens:
#         return "gasoline"
#     if "hybrid" in tokens:
#         return "hybrid"
#     if "ev" in tokens or "electric" in tokens:
#         return "ev"
#     if "any" in tokens:
#         return "any"
#     return None
#
# def extract_body_type(text: str) -> Optional[str]:
#     tokens = set(_tokenize(text))
#     if "sedan" in tokens:
#         return "sedan"
#     if "suv" in tokens:
#         return "suv"
#     if "pickup" in tokens:
#         return "pickup"
#     if "bus" in tokens:
#         return "bus"
#     if "mpv" in tokens:
#         return "mpv"
#     if "hatchback" in tokens:
#         return "hatchback"
#     if "any" in tokens:
#         return "any"
#     return None
#
# def detect_feature_key(text: str) -> Optional[str]:
#     t = _normalize_text(text)
#     for key, meta in FEATURE_MAP.items():
#         for alias in meta.get("aliases", []):
#             if alias in t:
#                 return key
#     return None
#
# def _apply_model_aliases(text_norm: str) -> str:
#     toks = _tokenize(text_norm)
#     for tok in toks:
#         if tok in MODEL_ALIASES:
#             return MODEL_ALIASES[tok]
#     return ""
#
# def _find_rows_by_base_name(full_rows: List[Dict[str, Any]], base_norm: str) -> List[Tuple[str, Dict[str, Any]]]:
#     out: List[Tuple[str, Dict[str, Any]]] = []
#     base_norm = normalize_model_name(base_norm)
#     if not base_norm:
#         return out
#     base_tokens = set(_tokenize(base_norm))
#     for r in full_rows:
#         model_norm = normalize_model_name(str(r.get("model") or ""))
#         if not model_norm:
#             continue
#         btoks = set(_base_model_tokens(model_norm))
#         if btoks and btoks.issubset(base_tokens):
#             out.append((model_norm, r))
#     return out
#
# def detect_model_in_text(text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
#     t_norm = normalize_model_name(_normalize_text(text))
#     t_comp = _compact(t_norm)
#     t_tokens = set(t_norm.split())
#
#     user_fuel_pref = extract_fuel(t_norm)
#
#     alias_base = _apply_model_aliases(t_norm)
#     if alias_base:
#         candidates = _find_rows_by_base_name(full_rows, alias_base)
#         picked = _pick_best_variant(candidates, user_fuel_pref)
#         if picked:
#             return picked
#
#     best_exact = None
#     best_overlap = 0
#     base_candidates: List[Tuple[str, Dict[str, Any]]] = []
#
#     for r in full_rows:
#         model_raw = str(r.get("model") or "")
#         model_norm = normalize_model_name(model_raw)
#         if not model_norm:
#             continue
#
#         if model_norm in t_norm:
#             return model_norm
#
#         m_comp = _compact(model_norm)
#         if m_comp and m_comp in t_comp:
#             return model_norm
#
#         m_tokens = set(_model_tokens(model_norm))
#         overlap = len(m_tokens.intersection(t_tokens))
#         if overlap >= 2 and overlap > best_overlap:
#             best_overlap = overlap
#             best_exact = model_norm
#
#         base_tokens = _base_model_tokens(model_norm)
#         if base_tokens and all(bt in t_tokens for bt in base_tokens):
#             base_candidates.append((model_norm, r))
#
#     picked = _pick_best_variant(base_candidates, user_fuel_pref)
#     if picked:
#         return picked
#
#     phrase = _extract_after_of_phrase(text)
#     if phrase:
#         fuzzy_best, fuzzy_score = _best_fuzzy_model_match(phrase, full_rows)
#         if fuzzy_best and fuzzy_score >= 0.80:
#             return fuzzy_best
#
#     fuzzy_best, fuzzy_score = _best_fuzzy_model_match(text, full_rows)
#     if fuzzy_best and fuzzy_score >= 0.86:
#         return fuzzy_best
#
#     return best_exact
#
# def detect_models_in_text(text: str, full_rows: List[Dict[str, Any]], max_models: int = 3) -> List[str]:
#     t_norm = normalize_model_name(_normalize_text(text))
#     t_comp = _compact(t_norm)
#     t_tokens = set(t_norm.split())
#     user_fuel_pref = extract_fuel(t_norm)
#
#     found: List[Tuple[int, str]] = []  # (position, model_norm)
#     seen_models = set()
#     seen_base = set()
#
#     def add_model(model_norm: str, pos: int):
#         if not model_norm:
#             return
#         if model_norm in seen_models:
#             return
#         found.append((pos, model_norm))
#         seen_models.add(model_norm)
#
#     # A) Alias (vigo/viggo -> wigo)
#     alias_base = _apply_model_aliases(t_norm)
#     if alias_base:
#         picked = _pick_variant_for_base(full_rows, alias_base, user_fuel_pref)
#         if picked:
#             pos = t_norm.find(alias_base) if alias_base else 10**9
#             add_model(picked, pos)
#
#     # B) Exact / compact substring matches (fast path)
#     for r in full_rows:
#         model_norm = normalize_model_name(str(r.get("model") or ""))
#         if not model_norm:
#             continue
#
#         if model_norm in t_norm:
#             add_model(model_norm, t_norm.find(model_norm))
#         else:
#             m_comp = _compact(model_norm)
#             if m_comp and m_comp in t_comp:
#                 add_model(model_norm, t_comp.find(m_comp))
#
#         if len(found) >= max_models:
#             break
#
#     # C) Split by separators: "and", ",", "&", "vs"
#     if len(found) < max_models:
#         parts = re.split(r"\b(?:and|,|&|vs|versus)\b", t_norm)
#         for p in parts:
#             p = p.strip()
#             if not p:
#                 continue
#             m = detect_model_in_text(p, full_rows)
#             if m:
#                 pos = t_norm.find(p)
#                 add_model(m, pos if pos >= 0 else 10**8)
#             if len(found) >= max_models:
#                 break
#
#     # D) NEW: base-token family detection (handles: "yaris cross corolla cross vios")
#     # If user didn't separate model names, we detect families by base tokens subset in the query.
#     if len(found) < max_models:
#         # Build base families -> pick a variant for each base family
#         base_candidates: List[Tuple[int, str]] = []  # (pos, picked_model_norm)
#
#         for r in full_rows:
#             model_norm = normalize_model_name(str(r.get("model") or ""))
#             if not model_norm:
#                 continue
#
#             base_phrase = _base_key(model_norm)
#             if not base_phrase:
#                 continue
#
#             # Avoid repeating same base family
#             if base_phrase in seen_base:
#                 continue
#
#             base_tokens = set(base_phrase.split())
#             if base_tokens and base_tokens.issubset(t_tokens):
#                 # find approximate position using base phrase tokens (best effort)
#                 pos = 10**8
#                 # try locate any token in order
#                 first_tok = base_phrase.split()[0]
#                 i = t_norm.find(first_tok)
#                 if i >= 0:
#                     pos = i
#
#                 picked = _pick_variant_for_base(full_rows, base_phrase, user_fuel_pref)
#                 if picked:
#                     base_candidates.append((pos, picked))
#                     seen_base.add(base_phrase)
#
#         base_candidates.sort(key=lambda x: x[0])
#         for pos, picked in base_candidates:
#             add_model(picked, pos)
#             if len(found) >= max_models:
#                 break
#
#     # Keep original order as much as possible
#     found.sort(key=lambda x: x[0])
#     return [m for _, m in found[:max_models]]
#
# def prefer_last_model_if_close(mentioned_model_norm: Optional[str], last_model_norm: Optional[str]) -> Optional[str]:
#     if not mentioned_model_norm:
#         return None
#     if not last_model_norm:
#         return mentioned_model_norm
#     if mentioned_model_norm in last_model_norm:
#         return last_model_norm
#     return mentioned_model_norm
#
# def resolve_target_model(user_text: str, last_model: Optional[str], full_rows: List[Dict[str, Any]]) -> Optional[str]:
#     mentioned = detect_model_in_text(user_text, full_rows)
#     if mentioned:
#         return prefer_last_model_if_close(mentioned, last_model)
#
#     t = _normalize_text(user_text)
#
#     if t.startswith(("how about", "what about")):
#         rest = re.sub(r"^(how about|what about)\s+", "", t).strip()
#         mentioned2 = detect_model_in_text(rest, full_rows)
#         if mentioned2:
#             return prefer_last_model_if_close(mentioned2, last_model)
#         return None
#
#     if any(p in t for p in ["it", "this model", "that model", "this one", "the car"]):
#         return last_model
#
#     return last_model
#
# def yn_from_value(val: Any) -> Optional[bool]:
#     if val is None:
#         return None
#     s = str(val).strip().lower()
#     if not s:
#         return None
#     s = s.replace("_", " ").replace("-", " ")
#     s = re.sub(r"\s+", " ", s)
#
#     yes_values = {"yes", "true", "1", "available", "standard", "included", "present"}
#     no_values = {"no", "false", "0", "not available", "na", "n/a", "none", "absent"}
#
#     if s in yes_values or s.startswith("standard") or s.startswith("included"):
#         return True
#     if s in no_values or s.startswith("not"):
#         return False
#     return None
#
# def yn_label(val: Any) -> str:
#     yn = yn_from_value(val)
#     if yn is True:
#         return "Yes"
#     if yn is False:
#         return "No"
#     s = str(val).strip() if val is not None else ""
#     return s if s else "N/A"
#
# def answer_feature_from_csv(
#     full_rows: List[Dict[str, Any]],
#     model_norm: str,
#     feature_key: str,
# ) -> Optional[Dict[str, Any]]:
#     row = find_row_by_model(full_rows, model_norm)
#     if not row:
#         return None
#
#     model_name = row.get("model") or "This model"
#     src = row.get("url") or ""
#
#     meta = FEATURE_MAP.get(feature_key)
#     if not meta:
#         return None
#
#     for col in meta.get("columns", []):
#         val = row.get(col)
#         if val in (None, ""):
#             continue
#
#         if feature_key == "price":
#             value_txt = format_price_usd(val)
#             text = f"{model_name} — {meta['label']}: {value_txt}"
#             return {
#                 "answer_type": "csv_feature",
#                 "text": text,
#                 "value": value_txt,
#                 "facts": [text],
#                 "sources": [src] if src else [],
#                 "model": model_name,
#                 "feature": feature_key,
#             }
#
#         if feature_key == "turning_radius":
#             value_txt = str(val).strip()
#             text = f"{model_name} — {meta['label']}: {value_txt}"
#             return {
#                 "answer_type": "csv_feature",
#                 "text": text,
#                 "value": value_txt,
#                 "facts": [text],
#                 "sources": [src] if src else [],
#                 "model": model_name,
#                 "feature": feature_key,
#             }
#
#         yn = yn_from_value(val)
#         if yn is True:
#             value_txt = "Yes"
#             text = f"Yes — {model_name} has {meta['label']} (official specification)."
#         elif yn is False:
#             value_txt = "No"
#             text = f"No — {model_name} does not list {meta['label']} (official specification)."
#         else:
#             value_txt = str(val).strip()
#             text = f"{model_name} — {meta['label']}: {value_txt}"
#
#         return {
#             "answer_type": "csv_feature",
#             "text": text,
#             "value": value_txt,
#             "facts": [text],
#             "sources": [src] if src else [],
#             "model": model_name,
#             "feature": feature_key,
#         }
#
#     if feature_key == "camera_360":
#         value_txt = "No"
#         text = f"No — {model_name} does not list {FEATURE_MAP['camera_360']['label']} in the official specifications we captured."
#         return {
#             "answer_type": "csv_feature",
#             "text": text,
#             "value": value_txt,
#             "facts": [text],
#             "sources": [src] if src else [],
#             "model": model_name,
#             "feature": feature_key,
#         }
#
#     return None
#
# def is_recommendation_intent(text: str) -> bool:
#     t = _normalize_text(text)
#
#     if detect_feature_key(t) is not None:
#         return False
#
#     if re.search(r"\b(spec|specs|specification|details)\b", t):
#         return False
#
#     if extract_budget(t) is not None:
#         return True
#     if extract_seats(t) is not None:
#         return True
#     if extract_fuel(t) is not None:
#         return True
#     if extract_body_type(t) is not None:
#         return True
#
#     if any(k in t for k in ["recommend", "suggest", "buy", "looking for", "need a car", "budget"]):
#         return True
#
#     return False
#
# def _seats_value(row: Dict[str, Any]) -> Optional[int]:
#     v = to_int(row.get("seats"))
#     if v is not None:
#         return v
#     return to_int(row.get("spec_seating_capacity"))
#
# def filter_cars_split(
#     rows: List[Dict[str, Any]],
#     max_budget: int,
#     min_seats: int,
#     fuel: str,
#     body_type: str,
# ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
#     fuel = (fuel or "any").lower().strip()
#     body_type = (body_type or "any").lower().strip()
#
#     verified: List[Dict[str, Any]] = []
#     possible: List[Dict[str, Any]] = []
#
#     for r in rows:
#         price = to_int(r.get("price_usd"))
#         if price is None or price > max_budget:
#             continue
#
#         row_fuel = (r.get("fuel") or "").lower().strip()
#         row_body = (r.get("body_type") or "").lower().strip()
#
#         if fuel != "any" and row_fuel != fuel:
#             continue
#         if body_type != "any" and row_body != body_type:
#             continue
#
#         seats_val = _seats_value(r)
#         if seats_val is None:
#             possible.append(r)
#             continue
#
#         if seats_val < min_seats:
#             continue
#
#         verified.append(r)
#
#     verified.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
#     possible.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
#     return verified, possible
#
# def build_reco_answer(
#     verified: List[Dict[str, Any]],
#     possible: List[Dict[str, Any]],
#     max_items: int = 5,
#     assumed_seats: Optional[int] = None,
# ) -> Dict[str, Any]:
#     if not verified and not possible:
#         return {
#             "answer_type": "csv_reco",
#             "text": "I couldn't find an official match with those constraints. Try increasing budget, lowering seats, changing body type, or using fuel = Any.",
#             "facts": [],
#             "sources": [],
#         }
#
#     lines: List[str] = []
#     sources: List[str] = []
#
#     if verified:
#         lines.append("Based on your requirements, here are official matches:\n")
#         for m in verified[:max_items]:
#             brand = m.get("brand", "")
#             model = m.get("model", "")
#             price_txt = format_price_usd(m.get("price_usd"))
#             seats_val = _seats_value(m)
#             seats_txt = str(seats_val) if seats_val is not None else "N/A"
#             f = m.get("fuel", "")
#             body = m.get("body_type", "")
#             url = m.get("url", "")
#
#             lines.append(f"- {brand} {model} ({price_txt}), seats={seats_txt}, fuel={f}, body={body}")
#             if url:
#                 sources.append(url)
#
#     if possible:
#         if lines:
#             lines.append("")
#         lines.append("Possible matches (some required fields are N/A in CSV):\n")
#         for m in possible[:max_items]:
#             brand = m.get("brand", "")
#             model = m.get("model", "")
#             price_txt = format_price_usd(m.get("price_usd"))
#             seats_val = _seats_value(m)
#             seats_txt = str(seats_val) if seats_val is not None else "N/A"
#             f = m.get("fuel", "")
#             body = m.get("body_type", "")
#             url = m.get("url", "")
#
#             lines.append(f"- {brand} {model} ({price_txt}), seats={seats_txt}, fuel={f}, body={body}")
#             if url:
#                 sources.append(url)
#
#     if assumed_seats is not None:
#         lines.append("")
#         lines.append(f"Note: I assumed {assumed_seats} seats. If you want 7 seats, type: 7 seats.")
#
#     return {
#         "answer_type": "csv_reco",
#         "text": "\n".join(lines).strip(),
#         "facts": [],
#         "sources": sources,
#     }
# def _base_key(model_norm: str) -> str:
#     base = _base_model_tokens(model_norm)
#     return " ".join(base)
#
# def _pick_variant_for_base(
#     full_rows: List[Dict[str, Any]],
#     base_phrase: str,
#     user_fuel_pref: Optional[str],
# ) -> Optional[str]:
#     candidates = _find_rows_by_base_name(full_rows, base_phrase)
#     return _pick_best_variant(candidates, user_fuel_pref)
# def is_summary_intent(text: str) -> bool:
#     t = _normalize_text(text)
#     keys = [
#         "safety system", "safety systems", "safety feature", "safety features",
#         "safety", "adas", "driver assist", "driver assistance", "toyota safety sense", "tss",
#     ]
#     return any(k in t for k in keys)
#
# def answer_specs_from_csv(full_rows: List[Dict[str, Any]], model_norm: str, max_lines: int = 12) -> Optional[Dict[str, Any]]:
#     row = find_row_by_model(full_rows, model_norm)
#     if not row:
#         return None
#
#     model_name = row.get("model") or "This model"
#     src = row.get("url") or ""
#
#     lines: List[str] = []
#     # Always show these if available
#     price = row.get("price_usd")
#     if price not in (None, ""):
#         lines.append(f"- Price (USD): {format_price_usd(price)}")
#
#     seats = _seats_value(row)
#     if seats is not None:
#         lines.append(f"- Seats: {seats}")
#
#     fuel = (row.get("fuel") or "").strip()
#     if fuel:
#         lines.append(f"- Fuel: {fuel}")
#
#     body = (row.get("body_type") or "").strip()
#     if body:
#         lines.append(f"- Body type: {body}")
#
#     # Add a small set of “useful” spec fields if they exist in your CSV
#     # (these keys depend on how you generated the CSV; add/remove as needed)
#     extra_fields = [
#         ("Engine type", "spec_engine_type"),
#         ("Transmission", "spec_transmission_type"),
#         ("Displacement", "spec_displacement"),
#         ("Maximum output", "spec_maximum_output"),
#         ("Maximum torque", "spec_maximum_torque"),
#         ("Fuel tank", "spec_fuel_tank_capacity"),
#         ("Ground clearance", "spec_ground_clearance"),
#         ("Turning radius", "spec_minimum_turning_radius_tire"),
#         ("Apple CarPlay/Android Auto", "spec_apple_carplay_and_android_auto"),
#         ("Reverse camera", "spec_reverse_camera"),
#         ("BSM", "spec_blind_spot_monitor_bsm"),
#         ("PVM", "spec_panoramic_view_monitor_pvm"),
#     ]
#
#     for label, col in extra_fields:
#         if len(lines) >= max_lines:
#             break
#         v = row.get(col)
#         if v in (None, ""):
#             continue
#         # For yes/no style fields, format nicely
#         if col.startswith("spec_") and any(x in col for x in ["camera", "bsm", "pvm", "carplay"]):
#             lines.append(f"- {label}: {yn_label(v)}")
#         else:
#             lines.append(f"- {label}: {str(v).strip()}")
#
#     if not lines:
#         return {
#             "answer_type": "csv_feature",
#             "text": f"I couldn't find structured specs for {model_name} in the CSV.",
#             "facts": [],
#             "sources": [src] if src else [],
#         }
#
#     text = f"{model_name} — key specifications (official data):\n" + "\n".join(lines)
#
#     return {
#         "answer_type": "csv_feature",
#         "text": text,
#         "facts": [text],
#         "sources": [src] if src else [],
#         "model": model_name,
#         "feature": "spec",
#     }
#
# def is_spec_intent(text: str) -> bool:
#     t = _normalize_text(text)
#     return bool(re.search(r"\b(spec|specs|specification|specifications|detail|details)\b", t))
# def _build_safety_summary(row: Dict[str, Any]) -> List[str]:
#     lines: List[str] = []
#
#     def add(label: str, col: str):
#         v = row.get(col)
#         if v not in (None, ""):
#             lines.append(f"- {label}: {yn_label(v)}")
#
#     add("ABS", "spec_antilock_braking_system_abs")
#     add("Vehicle Stability Control (VSC)", "spec_vehicle_stability_control_vsc")
#     add("SRS Airbags", "spec_srs_airbags")
#     add("Blind Spot Monitor (BSM)", "spec_blind_spot_monitor_bsm")
#     add("Lane Departure Warning (LDW)", "spec_lane_departure_warning_ldw")
#     add("Lane Keeping Control (LKC)", "spec_lane_keeping_control_lkc")
#     add("Pre-Collision Warning (PCW)", "spec_precollision_warning_pcw")
#     add("Pre-Collision Braking (PCB)", "spec_precollision_braking_pcb")
#     add("Reverse Camera", "spec_reverse_camera")
#     add("Panoramic View Monitor (PVM)", "spec_panoramic_view_monitor_pvm")
#
#     sr = str(row.get("spec_safety_rating") or "").strip()
#     if sr:
#         lines.append(f"- Safety Rating: {sr}")
#
#     return lines
#
# def answer_summary_from_csv(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
#     row = find_row_by_model(full_rows, model_norm)
#     if not row:
#         return None
#
#     model_name = row.get("model") or "This model"
#     src = row.get("url") or ""
#
#     lines = _build_safety_summary(row)
#     if not lines:
#         text = f"I couldn't find structured safety fields for {model_name} in the CSV."
#     else:
#         text = f"{model_name} — Safety systems (official CSV):\n" + "\n".join(lines)
#
#     return {
#         "answer_type": "csv_summary",
#         "text": text,
#         "facts": [text],
#         "sources": [src] if src else [],
#         "model": model_name,
#         "summary_type": "safety",
#     }
# New udpate for 09th-Feb-2026
# scripts/csv_engine.py
import csv
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FULL = PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv"

FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}
BODY_TYPES = {"suv", "sedan", "pickup", "bus", "mpv", "mvp", "van", "hatchback", "any"}

MODEL_STOP_TOKENS = {
    "hev", "hybrid", "electric", "ev",
    "gasoline", "diesel",
    "mt", "at", "manual", "automatic", "transmission",
    "edition", "legender", "rally", "gr", "gr-s", "zx", "vx", "vxr",
    "seater", "seaters",
}

MODEL_ALIASES: Dict[str, str] = {
    "vigo": "wigo",
    "viggo": "wigo",
    "wiggo": "wigo",
}

FEATURE_MAP: Dict[str, Dict[str, Any]] = {
    "pvm": {
        "aliases": ["pvm", "panoramic view monitor", "panoramic view", "around view monitor"],
        "columns": ["spec_panoramic_view_monitor_pvm"],
        "label": "Panoramic View Monitor (PVM)",
    },
    "camera_360": {
        "aliases": [
            "360 camera", "camera 360", "360-degree camera", "360° camera",
            "surround view camera", "surround-view camera",
            "birds eye camera", "bird view camera",
        ],
        "columns": [],
        "label": "360° surround-view camera",
    },
    "reverse_camera": {
        "aliases": ["reverse camera", "rear camera", "backup camera", "reversing camera"],
        "columns": ["spec_reverse_camera"],
        "label": "Reverse camera",
    },
    "adaptive_cruise": {
        "aliases": ["adaptive cruise", "acc", "drcc", "radar cruise", "dynamic radar cruise", "cruise control"],
        "columns": [
            "spec_fullspeed_range_adaptive_cruise_control_acc",
            "spec_dynamic_radar_cruise_control_drcc",
            "spec_cruise_control",
        ],
        "label": "Cruise control",
    },
    "bsm": {
        "aliases": ["blind spot", "bsm", "blind spot monitor"],
        "columns": ["spec_blind_spot_monitor_bsm"],
        "label": "Blind Spot Monitor (BSM)",
    },
    "carplay_android": {
        "aliases": ["carplay", "apple carplay", "android auto"],
        "columns": ["spec_apple_carplay_and_android_auto", "spec_apple_carplay_or_android_auto"],
        "label": "Apple CarPlay / Android Auto",
    },
    "turning_radius": {
        "aliases": [
            "turning radius", "minimum turning radius", "min turning radius",
            "turning circle", "minimum turning circle",
        ],
        "columns": ["spec_minimum_turning_radius_tire"],
        "label": "Minimum turning radius",
    },
    "wireless_charging": {
        "aliases": ["wireless charging", "wireless charger", "qi", "charging pad"],
        "columns": ["spec_wireless_charging", "spec_wireless_charger", "spec_wireless_charging", "spec_wireless_charger"],
        "label": "Wireless charging",
    },
    "ambient_lighting": {
        "aliases": ["ambient lighting", "ambient light", "mood lighting"],
        "columns": ["spec_ambient_lighting", "Ambient lighting"],
        "label": "Ambient lighting",
    },
    "price": {
        "aliases": ["price", "cost", "how much", "selling price", "usd", "$"],
        "columns": ["price_usd"],
        "label": "Price (USD)",
    },
}

def load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def load_full_rows() -> List[Dict[str, Any]]:
    return load_csv(CSV_FULL)

def normalize_model_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())

def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def to_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        s = s.replace(",", "")
        return int(float(s))
    except Exception:
        return None

def format_price_usd(v: Any) -> str:
    n = to_int(v)
    if n is None:
        s = str(v).strip() if v is not None else ""
        return s if s else "N/A"
    return f"${n:,}"

def _squeeze_repeats(text: str) -> str:
    return re.sub(r"(.)\1{2,}", r"\1\1", text)

def _normalize_text(text: str) -> str:
    t = (text or "").lower()
    t = _squeeze_repeats(t)

    t = re.sub(r"\bseadan\b", "sedan", t)
    t = re.sub(r"\bsaloon\b", "sedan", t)
    t = re.sub(r"\bmpvs?\b", "mpv", t)
    t = re.sub(r"\bmvp\b", "mpv", t)
    t = re.sub(r"\bmini\s*van\b", "van", t)
    t = re.sub(r"\bpick[\s\-]?up\b", "pickup", t)
    t = re.sub(r"\bvan\b", "bus", t)

    t = re.sub(r"\bdisel\b", "diesel", t)
    t = re.sub(r"\bdissel\b", "diesel", t)
    t = re.sub(r"\bgazoline\b", "gasoline", t)
    t = re.sub(r"\bgasolin\b", "gasoline", t)
    t = re.sub(r"\bpetrol\b", "gasoline", t)
    t = re.sub(r"\bhybird\b", "hybrid", t)
    t = re.sub(r"\bhev\b", "hybrid", t)

    return t

def _tokenize(text: str) -> List[str]:
    t = _normalize_text(text)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.split()

def _model_tokens(model_norm: str) -> List[str]:
    return [t for t in re.split(r"\s+", (model_norm or "").strip()) if t]

def _base_model_tokens(model_norm: str) -> List[str]:
    toks = _model_tokens(model_norm)
    base = [t for t in toks if t not in MODEL_STOP_TOKENS]
    return base if base else toks

def _extract_after_of_phrase(text: str) -> Optional[str]:
    t = _normalize_text(text)
    m = re.search(r"\bof\s+([a-z0-9\s\-]+)$", t)
    if not m:
        return None
    phrase = (m.group(1) or "").strip()
    return phrase if phrase else None

def _best_fuzzy_model_match(user_text: str, full_rows: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
    t = _normalize_text(user_text)
    t_comp = _compact(t)
    if not t_comp:
        return None, 0.0

    best_model = None
    best_score = 0.0

    for r in full_rows:
        model_norm = normalize_model_name(str(r.get("model") or ""))
        if not model_norm:
            continue
        m_comp = _compact(model_norm)
        if not m_comp:
            continue
        score = difflib.SequenceMatcher(None, t_comp, m_comp).ratio()
        if score > best_score:
            best_score = score
            best_model = model_norm

    return best_model, best_score

def find_row_by_model(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
    for r in full_rows:
        if normalize_model_name(r.get("model")) == model_norm:
            return r
    return None

def _row_fuel(row: Dict[str, Any]) -> str:
    return (row.get("fuel") or "").strip().lower()

def _pick_best_variant(
    candidates: List[Tuple[str, Dict[str, Any]]],
    user_fuel_pref: Optional[str],
) -> Optional[str]:
    if not candidates:
        return None

    if user_fuel_pref and user_fuel_pref in FUELS and user_fuel_pref != "any":
        filtered = [c for c in candidates if _row_fuel(c[1]) == user_fuel_pref]
        if filtered:
            candidates = filtered

    candidates_sorted = sorted(
        candidates,
        key=lambda x: (to_int(x[1].get("price_usd")) if to_int(x[1].get("price_usd")) is not None else 10**12)
    )
    return candidates_sorted[0][0]

def extract_budget(text: str) -> Optional[int]:
    m = re.search(r"\$?\s*([\d,]{4,})", text or "", flags=re.IGNORECASE)
    if not m:
        return None
    n = m.group(1).replace(",", "")
    return int(n) if n.isdigit() else None

def extract_seats(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:seat|seats|seater)\b", text or "", flags=re.IGNORECASE)
    return int(m.group(1)) if m else None

def extract_fuel(text: str) -> Optional[str]:
    tokens = set(_tokenize(text))
    if "diesel" in tokens:
        return "diesel"
    if "gasoline" in tokens:
        return "gasoline"
    if "hybrid" in tokens:
        return "hybrid"
    if "ev" in tokens or "electric" in tokens:
        return "ev"
    if "any" in tokens:
        return "any"
    return None

def extract_body_type(text: str) -> Optional[str]:
    tokens = set(_tokenize(text))
    if "sedan" in tokens:
        return "sedan"
    if "suv" in tokens:
        return "suv"
    if "pickup" in tokens:
        return "pickup"
    if "bus" in tokens:
        return "bus"
    if "mpv" in tokens:
        return "mpv"
    if "hatchback" in tokens:
        return "hatchback"
    if "any" in tokens:
        return "any"
    return None

def detect_feature_key(text: str) -> Optional[str]:
    t = _normalize_text(text)
    for key, meta in FEATURE_MAP.items():
        for alias in meta.get("aliases", []):
            if alias in t:
                return key
    return None

def _apply_model_aliases(text_norm: str) -> str:
    toks = _tokenize(text_norm)
    for tok in toks:
        if tok in MODEL_ALIASES:
            return MODEL_ALIASES[tok]
    return ""

def _find_rows_by_base_name(full_rows: List[Dict[str, Any]], base_norm: str) -> List[Tuple[str, Dict[str, Any]]]:
    out: List[Tuple[str, Dict[str, Any]]] = []
    base_norm = normalize_model_name(base_norm)
    if not base_norm:
        return out
    base_tokens = set(_tokenize(base_norm))
    for r in full_rows:
        model_norm = normalize_model_name(str(r.get("model") or ""))
        if not model_norm:
            continue
        btoks = set(_base_model_tokens(model_norm))
        if btoks and btoks.issubset(base_tokens):
            out.append((model_norm, r))
    return out

def detect_model_in_text(text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
    t_norm = normalize_model_name(_normalize_text(text))
    t_comp = _compact(t_norm)
    t_tokens = set(t_norm.split())

    user_fuel_pref = extract_fuel(t_norm)

    alias_base = _apply_model_aliases(t_norm)
    if alias_base:
        candidates = _find_rows_by_base_name(full_rows, alias_base)
        picked = _pick_best_variant(candidates, user_fuel_pref)
        if picked:
            return picked

    best_exact = None
    best_overlap = 0
    base_candidates: List[Tuple[str, Dict[str, Any]]] = []

    for r in full_rows:
        model_raw = str(r.get("model") or "")
        model_norm = normalize_model_name(model_raw)
        if not model_norm:
            continue

        if model_norm in t_norm:
            return model_norm

        m_comp = _compact(model_norm)
        if m_comp and m_comp in t_comp:
            return model_norm

        m_tokens = set(_model_tokens(model_norm))
        overlap = len(m_tokens.intersection(t_tokens))
        if overlap >= 2 and overlap > best_overlap:
            best_overlap = overlap
            best_exact = model_norm

        base_tokens = _base_model_tokens(model_norm)
        if base_tokens and all(bt in t_tokens for bt in base_tokens):
            base_candidates.append((model_norm, r))

    picked = _pick_best_variant(base_candidates, user_fuel_pref)
    if picked:
        return picked

    phrase = _extract_after_of_phrase(text)
    if phrase:
        fuzzy_best, fuzzy_score = _best_fuzzy_model_match(phrase, full_rows)
        if fuzzy_best and fuzzy_score >= 0.80:
            return fuzzy_best

    fuzzy_best, fuzzy_score = _best_fuzzy_model_match(text, full_rows)
    if fuzzy_best and fuzzy_score >= 0.86:
        return fuzzy_best

    return best_exact

def _base_key(model_norm: str) -> str:
    base = _base_model_tokens(model_norm)
    return " ".join(base)

def _pick_variant_for_base(
    full_rows: List[Dict[str, Any]],
    base_phrase: str,
    user_fuel_pref: Optional[str],
) -> Optional[str]:
    candidates = _find_rows_by_base_name(full_rows, base_phrase)
    return _pick_best_variant(candidates, user_fuel_pref)

def detect_models_in_text(text: str, full_rows: List[Dict[str, Any]], max_models: int = 3) -> List[str]:
    t_norm = normalize_model_name(_normalize_text(text))
    t_comp = _compact(t_norm)
    t_tokens = set(t_norm.split())
    user_fuel_pref = extract_fuel(t_norm)

    found: List[Tuple[int, str]] = []
    seen_models = set()
    seen_base = set()

    def add_model(model_norm: str, pos: int):
        if not model_norm:
            return
        if model_norm in seen_models:
            return
        found.append((pos, model_norm))
        seen_models.add(model_norm)

    alias_base = _apply_model_aliases(t_norm)
    if alias_base:
        picked = _pick_variant_for_base(full_rows, alias_base, user_fuel_pref)
        if picked:
            pos = t_norm.find(alias_base) if alias_base else 10**9
            add_model(picked, pos)

    for r in full_rows:
        model_norm = normalize_model_name(str(r.get("model") or ""))
        if not model_norm:
            continue

        if model_norm in t_norm:
            add_model(model_norm, t_norm.find(model_norm))
        else:
            m_comp = _compact(model_norm)
            if m_comp and m_comp in t_comp:
                add_model(model_norm, t_comp.find(m_comp))

        if len(found) >= max_models:
            break

    if len(found) < max_models:
        parts = re.split(r"\b(?:and|,|&|vs|versus)\b", t_norm)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            m = detect_model_in_text(p, full_rows)
            if m:
                pos = t_norm.find(p)
                add_model(m, pos if pos >= 0 else 10**8)
            if len(found) >= max_models:
                break

    if len(found) < max_models:
        base_candidates: List[Tuple[int, str]] = []

        for r in full_rows:
            model_norm = normalize_model_name(str(r.get("model") or ""))
            if not model_norm:
                continue

            base_phrase = _base_key(model_norm)
            if not base_phrase:
                continue

            if base_phrase in seen_base:
                continue

            base_tokens = set(base_phrase.split())
            if base_tokens and base_tokens.issubset(t_tokens):
                pos = 10**8
                first_tok = base_phrase.split()[0]
                i = t_norm.find(first_tok)
                if i >= 0:
                    pos = i

                picked = _pick_variant_for_base(full_rows, base_phrase, user_fuel_pref)
                if picked:
                    base_candidates.append((pos, picked))
                    seen_base.add(base_phrase)

        base_candidates.sort(key=lambda x: x[0])
        for pos, picked in base_candidates:
            add_model(picked, pos)
            if len(found) >= max_models:
                break

    found.sort(key=lambda x: x[0])
    return [m for _, m in found[:max_models]]

def prefer_last_model_if_close(mentioned_model_norm: Optional[str], last_model_norm: Optional[str]) -> Optional[str]:
    if not mentioned_model_norm:
        return None
    if not last_model_norm:
        return mentioned_model_norm
    if mentioned_model_norm in last_model_norm:
        return last_model_norm
    return mentioned_model_norm

def resolve_target_model(user_text: str, last_model: Optional[str], full_rows: List[Dict[str, Any]]) -> Optional[str]:
    mentioned = detect_model_in_text(user_text, full_rows)
    if mentioned:
        return prefer_last_model_if_close(mentioned, last_model)

    t = _normalize_text(user_text)

    if t.startswith(("how about", "what about")):
        rest = re.sub(r"^(how about|what about)\s+", "", t).strip()
        mentioned2 = detect_model_in_text(rest, full_rows)
        if mentioned2:
            return prefer_last_model_if_close(mentioned2, last_model)
        return None

    if any(p in t for p in ["it", "this model", "that model", "this one", "the car"]):
        return last_model

    return last_model

def yn_from_value(val: Any) -> Optional[bool]:
    if val is None:
        return None
    s = str(val).strip().lower()
    if not s:
        return None
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s)

    yes_values = {"yes", "true", "1", "available", "standard", "included", "present"}
    no_values = {"no", "false", "0", "not available", "na", "n/a", "none", "absent"}

    if s in yes_values or s.startswith("standard") or s.startswith("included"):
        return True
    if s in no_values or s.startswith("not"):
        return False
    return None

def yn_label(val: Any) -> str:
    yn = yn_from_value(val)
    if yn is True:
        return "Yes"
    if yn is False:
        return "No"
    s = str(val).strip() if val is not None else ""
    return s if s else "N/A"

def answer_feature_from_csv(
    full_rows: List[Dict[str, Any]],
    model_norm: str,
    feature_key: str,
) -> Optional[Dict[str, Any]]:
    row = find_row_by_model(full_rows, model_norm)
    if not row:
        return None

    model_name = row.get("model") or "This model"
    src = row.get("url") or ""

    meta = FEATURE_MAP.get(feature_key)
    if not meta:
        return None

    for col in meta.get("columns", []):
        val = row.get(col)
        if val in (None, ""):
            continue

        if feature_key == "price":
            value_txt = format_price_usd(val)
            text = f"{model_name} — {meta['label']}: {value_txt}"
            return {"answer_type": "csv_feature", "text": text, "value": value_txt, "facts": [text], "sources": [src] if src else []}

        if feature_key == "turning_radius":
            value_txt = str(val).strip()
            text = f"{model_name} — {meta['label']}: {value_txt}"
            return {"answer_type": "csv_feature", "text": text, "value": value_txt, "facts": [text], "sources": [src] if src else []}

        yn = yn_from_value(val)
        if yn is True:
            text = f"Yes — {model_name} has {meta['label']} (official specification)."
        elif yn is False:
            text = f"No — {model_name} does not list {meta['label']} (official specification)."
        else:
            text = f"{model_name} — {meta['label']}: {str(val).strip()}"

        return {"answer_type": "csv_feature", "text": text, "facts": [text], "sources": [src] if src else []}

    if feature_key == "camera_360":
        text = f"No — {model_name} does not list {FEATURE_MAP['camera_360']['label']} in the official specifications we captured."
        return {"answer_type": "csv_feature", "text": text, "facts": [text], "sources": [src] if src else []}

    return None

def is_recommendation_intent(text: str) -> bool:
    t = _normalize_text(text)

    if detect_feature_key(t) is not None:
        return False

    if re.search(r"\b(spec|specs|specification|details)\b", t):
        return False

    if extract_budget(t) is not None:
        return True
    if extract_seats(t) is not None:
        return True
    if extract_fuel(t) is not None:
        return True
    if extract_body_type(t) is not None:
        return True

    if any(k in t for k in ["recommend", "suggest", "buy", "looking for", "need a car", "budget"]):
        return True

    return False

def _seats_value(row: Dict[str, Any]) -> Optional[int]:
    v = to_int(row.get("seats"))
    if v is not None:
        return v
    return to_int(row.get("spec_seating_capacity"))

def filter_cars_split(
    rows: List[Dict[str, Any]],
    max_budget: int,
    min_seats: int,
    fuel: str,
    body_type: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    fuel = (fuel or "any").lower().strip()
    body_type = (body_type or "any").lower().strip()

    verified: List[Dict[str, Any]] = []
    possible: List[Dict[str, Any]] = []

    for r in rows:
        price = to_int(r.get("price_usd"))
        if price is None or price > max_budget:
            continue

        row_fuel = (r.get("fuel") or "").lower().strip()
        row_body = (r.get("body_type") or "").lower().strip()

        if fuel != "any" and row_fuel != fuel:
            continue
        if body_type != "any" and row_body != body_type:
            continue

        seats_val = _seats_value(r)
        if seats_val is None:
            possible.append(r)
            continue

        if seats_val < min_seats:
            continue

        verified.append(r)

    verified.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
    possible.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
    return verified, possible

def build_reco_answer(
    verified: List[Dict[str, Any]],
    possible: List[Dict[str, Any]],
    max_items: int = 5,
    assumed_seats: Optional[int] = None,
) -> Dict[str, Any]:
    if not verified and not possible:
        return {"answer_type": "csv_reco", "text": "I couldn't find an official match with those constraints.", "facts": [], "sources": []}

    lines: List[str] = []
    sources: List[str] = []

    if verified:
        lines.append("Based on your requirements, here are official matches:\n")
        for m in verified[:max_items]:
            model = m.get("model", "")
            price_txt = format_price_usd(m.get("price_usd"))
            seats_val = _seats_value(m)
            seats_txt = str(seats_val) if seats_val is not None else "N/A"
            f = m.get("fuel", "")
            body = m.get("body_type", "")
            url = m.get("url", "")
            lines.append(f"- {model} ({price_txt}), seats={seats_txt}, fuel={f}, body={body}")
            if url:
                sources.append(url)

    if possible:
        if lines:
            lines.append("")
        lines.append("Possible matches (some required fields are N/A in CSV):\n")
        for m in possible[:max_items]:
            model = m.get("model", "")
            price_txt = format_price_usd(m.get("price_usd"))
            seats_val = _seats_value(m)
            seats_txt = str(seats_val) if seats_val is not None else "N/A"
            f = m.get("fuel", "")
            body = m.get("body_type", "")
            url = m.get("url", "")
            lines.append(f"- {model} ({price_txt}), seats={seats_txt}, fuel={f}, body={body}")
            if url:
                sources.append(url)

    if assumed_seats is not None:
        lines.append("")
        lines.append(f"Note: I assumed {assumed_seats} seats. If you want 7 seats, type: 7 seats.")

    return {"answer_type": "csv_reco", "text": "\n".join(lines).strip(), "facts": [], "sources": sources}

def is_summary_intent(text: str) -> bool:
    t = _normalize_text(text)
    keys = [
        "safety system", "safety systems", "safety feature", "safety features",
        "safety", "adas", "driver assist", "driver assistance", "toyota safety sense", "tss",
    ]
    return any(k in t for k in keys)

def answer_specs_from_csv(full_rows: List[Dict[str, Any]], model_norm: str, max_lines: int = 12) -> Optional[Dict[str, Any]]:
    row = find_row_by_model(full_rows, model_norm)
    if not row:
        return None

    model_name = row.get("model") or "This model"
    src = row.get("url") or ""

    lines: List[str] = []
    price = row.get("price_usd")
    if price not in (None, ""):
        lines.append(f"- Price (USD): {format_price_usd(price)}")

    seats = _seats_value(row)
    if seats is not None:
        lines.append(f"- Seats: {seats}")

    fuel = (row.get("fuel") or "").strip()
    if fuel:
        lines.append(f"- Fuel: {fuel}")

    body = (row.get("body_type") or "").strip()
    if body:
        lines.append(f"- Body type: {body}")

    extra_fields = [
        ("Engine type", "spec_engine_type"),
        ("Transmission", "spec_transmission_type"),
        ("Displacement", "spec_displacement"),
        ("Maximum output", "spec_maximum_output"),
        ("Maximum torque", "spec_maximum_torque"),
        ("Fuel tank", "spec_fuel_tank_capacity"),
        ("Ground clearance", "spec_ground_clearance"),
        ("Turning radius", "spec_minimum_turning_radius_tire"),
        ("Apple CarPlay/Android Auto", "spec_apple_carplay_and_android_auto"),
        ("Reverse camera", "spec_reverse_camera"),
        ("BSM", "spec_blind_spot_monitor_bsm"),
        ("PVM", "spec_panoramic_view_monitor_pvm"),
        ("Wireless charging", "spec_wireless_charging"),
    ]

    for label, col in extra_fields:
        if len(lines) >= max_lines:
            break
        v = row.get(col)
        if v in (None, ""):
            continue
        if col.startswith("spec_") and any(x in col for x in ["camera", "bsm", "pvm", "carplay", "wireless"]):
            lines.append(f"- {label}: {yn_label(v)}")
        else:
            lines.append(f"- {label}: {str(v).strip()}")

    text = f"{model_name} — key specifications (official data):\n" + "\n".join(lines)
    return {"answer_type": "csv_feature", "text": text, "facts": [text], "sources": [src] if src else []}

def is_spec_intent(text: str) -> bool:
    t = _normalize_text(text)
    return bool(re.search(r"\b(spec|specs|specification|specifications|detail|details)\b", t))

def _build_safety_summary(row: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    def add(label: str, col: str):
        v = row.get(col)
        if v not in (None, ""):
            lines.append(f"- {label}: {yn_label(v)}")

    add("ABS", "spec_antilock_braking_system_abs")
    add("Vehicle Stability Control (VSC)", "spec_vehicle_stability_control_vsc")
    add("SRS Airbags", "spec_srs_airbags")
    add("Blind Spot Monitor (BSM)", "spec_blind_spot_monitor_bsm")
    add("Lane Departure Warning (LDW)", "spec_lane_departure_warning_ldw")
    add("Lane Keeping Control (LKC)", "spec_lane_keeping_control_lkc")
    add("Pre-Collision Warning (PCW)", "spec_precollision_warning_pcw")
    add("Pre-Collision Braking (PCB)", "spec_precollision_braking_pcb")
    add("Reverse Camera", "spec_reverse_camera")
    add("Panoramic View Monitor (PVM)", "spec_panoramic_view_monitor_pvm")

    sr = str(row.get("spec_safety_rating") or "").strip()
    if sr:
        lines.append(f"- Safety Rating: {sr}")

    return lines

def answer_summary_from_csv(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
    row = find_row_by_model(full_rows, model_norm)
    if not row:
        return None

    model_name = row.get("model") or "This model"
    src = row.get("url") or ""

    lines = _build_safety_summary(row)
    if not lines:
        text = f"I couldn't find structured safety fields for {model_name} in the CSV."
    else:
        text = f"{model_name} — Safety systems (official CSV):\n" + "\n".join(lines)

    return {"answer_type": "csv_summary", "text": text, "facts": [text], "sources": [src] if src else []}

def list_variants_for_model(full_rows: List[Dict[str, Any]], model_norm: str) -> List[Dict[str, Any]]:
    model_norm = normalize_model_name(model_norm or "")
    if not model_norm:
        return []

    row = find_row_by_model(full_rows, model_norm)
    if row:
        base_phrase = _base_key(model_norm)
    else:
        base_phrase = _base_key(model_norm)

    if not base_phrase:
        return []

    candidates = _find_rows_by_base_name(full_rows, base_phrase)

    out: List[Dict[str, Any]] = []
    for m_norm, r in candidates:
        out.append({
            "model_norm": m_norm,
            "model": r.get("model") or m_norm,
            "fuel": (r.get("fuel") or "").strip(),
            "price_usd": r.get("price_usd"),
            "url": r.get("url") or "",
        })

    out.sort(key=lambda x: (to_int(x.get("price_usd")) if to_int(x.get("price_usd")) is not None else 10**12))
    return out
# scripts/csv_engine.py
# Add this function at the bottom (or anywhere after find_row_by_model + normalize helpers)

from typing import Dict, Any, List

def list_variants_for_model(full_rows: List[Dict[str, Any]], model_norm: str) -> List[Dict[str, Any]]:
    """
    Return variants for the same base model family as model_norm.
    Example: yaris cross gasoline + yaris cross hev.
    """
    # local imports from existing functions in this file
    base = _base_key(model_norm)
    if not base:
        row = find_row_by_model(full_rows, model_norm)
        return [row] if row else []

    variants: List[Dict[str, Any]] = []
    base_tokens = set(_tokenize(base))

    for r in full_rows:
        m = normalize_model_name(str(r.get("model") or ""))
        if not m:
            continue
        m_base = _base_key(m)
        if not m_base:
            continue
        if set(_tokenize(m_base)) == base_tokens:
            variants.append(r)

    # sort by price
    variants.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
    return variants