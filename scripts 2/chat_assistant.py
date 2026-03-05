# # scripts/chat_assistant.py
# from typing import Dict, Any, List, Optional
# import re
#
# from scripts.csv_engine import (
#     load_full_rows,
#     detect_feature_key,
#     detect_model_in_text,
#     detect_models_in_text,
#     resolve_target_model,
#     answer_feature_from_csv,
#     is_recommendation_intent,
#     extract_budget,
#     extract_seats,
#     extract_fuel,
#     extract_body_type,
#     filter_cars_split,
#     build_reco_answer,
#     is_summary_intent,
#     answer_summary_from_csv,
#     is_spec_intent,
#     answer_specs_from_csv,
#     find_row_by_model,
#     format_price_usd,
# )
# from scripts.llm_client import llm_rewrite
# from scripts.rag_engine import RAGEngine
#
#
# def _is_small_talk(text: str) -> bool:
#     t = (text or "").strip().lower()
#     return t in {"hi", "hello", "hey", "hii", "hallo"} or t.startswith(("hi ", "hello ", "hey "))
#
#
# def _small_talk_reply() -> Dict[str, Any]:
#     text = (
#         "Hi! I can help you with:\n"
#         "- Recommend Toyota models by budget + fuel + body type (seats optional)\n"
#         "- Answer quick questions (price, turning radius, CarPlay/Android Auto, BSM, PVM, reverse camera, cruise control)\n"
#         "- Summarize safety systems\n"
#         "- Compare 2 models\n"
#         "Examples:\n"
#         "  recommend budget 50000 hybrid suv\n"
#         "  price of yaris cross hev\n"
#         "  turning radius of yaris cross\n"
#         "  compare yaris cross and corolla cross\n"
#     )
#     return {"answer_type": "system", "text": text, "facts": [], "sources": []}
#
#
# def _is_yes(text: str) -> bool:
#     t = (text or "").strip().lower()
#     return t in {"yes", "y", "ok", "okay", "sure", "pls", "please"}
#
#
# def _pipe(res: Dict[str, Any], pipeline: str, debug: bool) -> Dict[str, Any]:
#     if debug:
#         res = dict(res)
#         res["pipeline"] = pipeline
#     return res
#
#
# def _render_pipeline_tag(pipeline: str, debug: bool) -> str:
#     if not debug:
#         return ""
#     if not pipeline:
#         return ""
#     return f"\n[PIPELINE={pipeline}]"
#
#
# def _parse_compare_models(text: str, full_rows) -> List[str]:
#     return detect_models_in_text(text, full_rows, max_models=3)
#
#
# def _compare_models_from_csv(full_rows, model_a_norm: str, model_b_norm: str) -> Optional[Dict[str, Any]]:
#     row_a = find_row_by_model(full_rows, model_a_norm)
#     row_b = find_row_by_model(full_rows, model_b_norm)
#     if not row_a or not row_b:
#         return None
#
#     a_name = row_a.get("model") or model_a_norm
#     b_name = row_b.get("model") or model_b_norm
#     src_a = row_a.get("url") or ""
#     src_b = row_b.get("url") or ""
#
#     compare_fields = [
#         ("Price (USD)", "price_usd", "price"),
#         ("Body type", "body_type", None),
#         ("Seats", "seats", None),
#         ("Fuel", "fuel", None),
#         ("Minimum turning radius", "spec_minimum_turning_radius_tire", None),
#         ("Apple CarPlay / Android Auto", "spec_apple_carplay_and_android_auto", None),
#         ("Reverse camera", "spec_reverse_camera", None),
#         ("Panoramic View Monitor (PVM)", "spec_panoramic_view_monitor_pvm", None),
#         ("Blind Spot Monitor (BSM)", "spec_blind_spot_monitor_bsm", None),
#         ("Cruise control", "spec_cruise_control", None),
#     ]
#
#     diffs: List[str] = []
#     same: List[str] = []
#
#     for label, col, kind in compare_fields:
#         av = row_a.get(col)
#         bv = row_b.get(col)
#
#         if kind == "price":
#             a_txt = format_price_usd(av)
#             b_txt = format_price_usd(bv)
#         else:
#             a_txt = str(av).strip() if av not in (None, "") else "N/A"
#             b_txt = str(bv).strip() if bv not in (None, "") else "N/A"
#
#         line = f"- {label}: {a_txt} vs {b_txt}"
#         if a_txt.strip().lower() == b_txt.strip().lower():
#             same.append(line)
#         else:
#             diffs.append(line)
#
#     lines: List[str] = []
#     lines.append("Here’s a quick comparison (official specs):")
#     lines.append(f"{a_name} vs {b_name}")
#
#     if diffs:
#         lines.append("")
#         lines.append("Key differences:")
#         lines.extend(diffs)
#
#     if same:
#         lines.append("")
#         lines.append("Same on both models:")
#         lines.extend(same)
#
#     sources: List[str] = []
#     if src_a:
#         sources.append(src_a)
#     if src_b and src_b not in sources:
#         sources.append(src_b)
#
#     text = "\n".join(lines).strip()
#     return {"answer_type": "csv_compare", "text": text, "facts": [text], "sources": sources}
#
#
# def _reset_state(state: Dict[str, Any]) -> None:
#     state["last_model"] = None
#     state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
#     state["pending_compare"] = {"awaiting": False, "base_model_norm": None}
#     state["slot_fill_active"] = False
#     state["slot_fill_missing"] = []
#     state["last_reco"] = None
#
#
# def _has_last_reco(state: Dict[str, Any]) -> bool:
#     lr = state.get("last_reco")
#     if not lr:
#         return False
#     return lr.get("max_budget") is not None and lr.get("fuel") and lr.get("body_type")
#
#
# def _continue_reco_from_state(state: Dict[str, Any], full_rows, debug: bool) -> Dict[str, Any]:
#     slots = state["slots"]
#
#     need_budget = slots["max_budget"] is None
#     need_fuel = slots["fuel"] is None
#     need_body = slots["body_type"] is None
#
#     if need_budget or need_fuel or need_body:
#         missing = []
#         if need_budget:
#             missing.append("maximum budget (USD)")
#         if need_fuel:
#             missing.append("fuel (Diesel/Gasoline/Hybrid/EV/Any)")
#         if need_body:
#             missing.append("body type (SUV/Sedan/MPV/Pickup/Bus/Any)")
#
#         state["slot_fill_active"] = True
#         text = "To recommend from official data, please tell me: " + ", ".join(missing) + "."
#         return _pipe({"answer_type": "csv_reco", "text": text, "facts": [], "sources": []}, "CSV_METHOD", debug)
#
#     assumed_seats = None
#     if slots["min_seats"] is None:
#         slots["min_seats"] = 5
#         assumed_seats = 5
#
#     max_budget = int(slots["max_budget"])
#     min_seats = int(slots["min_seats"])
#     fuel = slots["fuel"]
#     body_type = slots["body_type"]
#
#     verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
#     ans = build_reco_answer(verified, possible, max_items=5, assumed_seats=assumed_seats)
#
#     state["last_reco"] = {
#         "max_budget": max_budget,
#         "min_seats": min_seats,
#         "fuel": fuel,
#         "body_type": body_type,
#     }
#
#     if verified:
#         state["last_model"] = (verified[0].get("model") or "").lower().strip() or state.get("last_model")
#     elif possible:
#         state["last_model"] = (possible[0].get("model") or "").lower().strip() or state.get("last_model")
#
#     state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
#     state["slot_fill_active"] = False
#     state["slot_fill_missing"] = []
#
#     return _pipe(ans, "CSV_METHOD", debug)
#
#
# def _cancel_reco_flow(state: Dict[str, Any]) -> None:
#     state["slot_fill_active"] = False
#     state["slot_fill_missing"] = []
#     state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
#
#
# def chat_turn(user_text: str, state: Dict[str, Any], full_rows, rag: RAGEngine, debug: bool) -> Dict[str, Any]:
#     user_text = (user_text or "").strip()
#     if not user_text:
#         return _pipe(
#             {"answer_type": "system", "text": "Please type a question or your requirements.", "facts": [], "sources": []},
#             "SYSTEM",
#             debug,
#         )
#
#     if user_text.lower().strip() == "/reset":
#         _reset_state(state)
#         return _pipe({"answer_type": "system", "text": "Reset done. Ask me anything.", "facts": [], "sources": []}, "SYSTEM", debug)
#
#     if _is_small_talk(user_text):
#         return _pipe(_small_talk_reply(), "SYSTEM", debug)
#
#     feature_key_now = detect_feature_key(user_text)
#     summary_now = is_summary_intent(user_text)
#     spec_now = is_spec_intent(user_text)
#
#     # Fuel-only follow-up like: "hev?", "diesel?", "gasoline?"
#     fuel_only = (user_text or "").strip().lower().rstrip("?").strip()
#     if fuel_only in {"hev", "hybrid", "diesel", "gasoline", "ev", "electric"} and state.get("last_model"):
#         fuel = extract_fuel(user_text)
#         if fuel:
#             variant = detect_model_in_text(f"{state['last_model']} {fuel}", full_rows)
#             if variant:
#                 state["last_model"] = variant
#                 # Prefer price as the most common follow-up after switching variant
#                 res = answer_feature_from_csv(full_rows, variant, "price")
#                 if res:
#                     _cancel_reco_flow(state)
#                     return _pipe(res, "CSV_METHOD", debug)
#
#     # Spec follow-up short keywords: "engine?", "dimensions?", "safety?", "transmission?"
#     if not spec_now and state.get("last_model"):
#         t = (user_text or "").strip().lower()
#         if re.fullmatch(r"(engine|dimensions|dimension|size|safety|interior|exterior|transmission|gearbox)\??", t):
#             spec_res = answer_specs_from_csv(full_rows, state["last_model"])
#             if spec_res:
#                 _cancel_reco_flow(state)
#                 return _pipe(spec_res, "CSV_METHOD", debug)
#
#     # If user asks for specs, answer specs and do not ask for budget/body.
#     if spec_now:
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#             spec_res = answer_specs_from_csv(full_rows, model_norm)
#             if spec_res:
#                 _cancel_reco_flow(state)
#                 return _pipe(spec_res, "CSV_METHOD", debug)
#
#         return _pipe(
#             {"answer_type": "system", "text": "Which Toyota model do you want specs for? Example: spec of Vios", "facts": [], "sources": []},
#             "SYSTEM",
#             debug,
#         )
#
#     if summary_now:
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#             csv_sum = answer_summary_from_csv(full_rows, model_norm)
#             if csv_sum:
#                 _cancel_reco_flow(state)
#                 return _pipe(csv_sum, "CSV_METHOD", debug)
#
#     # Multi-model price
#     if feature_key_now == "price":
#         models = detect_models_in_text(user_text, full_rows, max_models=3)
#         if models:
#             lines: List[str] = []
#             sources: List[str] = []
#             for m in models:
#                 res = answer_feature_from_csv(full_rows, m, "price")
#                 if res:
#                     lines.append(res["text"])
#                     for s in res.get("sources", []):
#                         if s and s not in sources:
#                             sources.append(s)
#             if lines:
#                 _cancel_reco_flow(state)
#                 return _pipe({"answer_type": "csv_feature_multi", "text": "\n".join(lines), "facts": lines, "sources": sources}, "CSV_METHOD", debug)
#
#     # Single feature
#     if feature_key_now and feature_key_now != "spec":
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#             csv_res = answer_feature_from_csv(full_rows, model_norm, feature_key_now)
#             if csv_res:
#                 _cancel_reco_flow(state)
#                 return _pipe(csv_res, "CSV_METHOD", debug)
#
#     # Compare
#     t_norm = user_text.lower().strip()
#     if t_norm.startswith("compare") or " vs " in t_norm or " versus " in t_norm:
#         models = _parse_compare_models(user_text, full_rows)
#         if len(models) >= 2:
#             res = _compare_models_from_csv(full_rows, models[0], models[1])
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#         state["pending_compare"] = {"awaiting": True, "base_model_norm": state.get("last_model")}
#         return _pipe(
#             {"answer_type": "system", "text": "Which two models do you want to compare? Example: compare yaris cross and corolla cross", "facts": [], "sources": []},
#             "SYSTEM",
#             debug,
#         )
#
#     if state.get("pending_compare", {}).get("awaiting") is True:
#         base_norm = state.get("pending_compare", {}).get("base_model_norm")
#         models = _parse_compare_models(user_text, full_rows)
#
#         if len(models) >= 2:
#             res = _compare_models_from_csv(full_rows, models[0], models[1])
#             state["pending_compare"] = {"awaiting": False, "base_model_norm": None}
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#             return _pipe({"answer_type": "system", "text": "I couldn’t build the comparison from CSV.", "facts": [], "sources": []}, "SYSTEM", debug)
#
#         if base_norm and len(models) == 1:
#             target = models[0]
#             if target == base_norm:
#                 return _pipe({"answer_type": "system", "text": "That’s the same model. Please choose a different model to compare.", "facts": [], "sources": []}, "SYSTEM", debug)
#             res = _compare_models_from_csv(full_rows, base_norm, target)
#             state["pending_compare"] = {"awaiting": False, "base_model_norm": None}
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#             return _pipe({"answer_type": "system", "text": "I couldn’t build the comparison from CSV.", "facts": [], "sources": []}, "SYSTEM", debug)
#
#         if _is_yes(user_text):
#             return _pipe({"answer_type": "system", "text": "Type the model name you want to compare with. Example: Corolla Cross HEV", "facts": [], "sources": []}, "SYSTEM", debug)
#
#         return _pipe({"answer_type": "system", "text": "Which model should I compare with? Please type the model name.", "facts": [], "sources": []}, "SYSTEM", debug)
#
#     # Follow-up refinement after recommendation
#     if _has_last_reco(state):
#         b = extract_budget(user_text)
#         s = extract_seats(user_text)
#         f = extract_fuel(user_text)
#         bt = extract_body_type(user_text)
#
#         if b is None and (s is not None or f is not None or bt is not None) and not is_recommendation_intent(user_text):
#             lr = dict(state["last_reco"])
#             if s is not None:
#                 lr["min_seats"] = s
#             if f is not None:
#                 lr["fuel"] = f
#             if bt is not None:
#                 lr["body_type"] = bt
#
#             state["slots"]["max_budget"] = lr["max_budget"]
#             state["slots"]["min_seats"] = lr["min_seats"]
#             state["slots"]["fuel"] = lr["fuel"]
#             state["slots"]["body_type"] = lr["body_type"]
#
#             return _continue_reco_from_state(state, full_rows, debug)
#
#     # Slot filling
#     if state.get("slot_fill_active") is True:
#         b = extract_budget(user_text)
#         s = extract_seats(user_text)
#         f = extract_fuel(user_text)
#         bt = extract_body_type(user_text)
#
#         if b is not None:
#             state["slots"]["max_budget"] = b
#         if s is not None:
#             state["slots"]["min_seats"] = s
#         if f is not None:
#             state["slots"]["fuel"] = f
#         if bt is not None:
#             state["slots"]["body_type"] = bt
#
#         return _continue_reco_from_state(state, full_rows, debug)
#
#     # Recommendation
#     if is_recommendation_intent(user_text):
#         b = extract_budget(user_text)
#         s = extract_seats(user_text)
#         f = extract_fuel(user_text)
#         bt = extract_body_type(user_text)
#
#         if b is not None:
#             state["slots"]["max_budget"] = b
#         if s is not None:
#             state["slots"]["min_seats"] = s
#         if f is not None:
#             state["slots"]["fuel"] = f
#         if bt is not None:
#             state["slots"]["body_type"] = bt
#
#         return _continue_reco_from_state(state, full_rows, debug)
#
#     # Track last model mention
#     mentioned_model = detect_model_in_text(user_text, full_rows)
#     if mentioned_model:
#         state["last_model"] = mentioned_model
#
#     return _pipe(rag.rag_answer(user_text, last_model_norm=state.get("last_model")), "RAG", debug)
#
#
# def render_answer(user_text: str, res: Dict[str, Any], use_llm: bool, rewrite_csv: bool, debug: bool) -> str:
#     text = (res.get("text") or "").strip()
#     facts = res.get("facts") or []
#     sources = res.get("sources") or []
#     pipeline = res.get("pipeline") or ""
#
#     if not text:
#         text = "I couldn't produce an answer."
#
#     if use_llm:
#         if pipeline == "CSV_METHOD" and not rewrite_csv:
#             if sources:
#                 text = text + "\nSources: " + ", ".join(sources)
#             return text + _render_pipeline_tag(pipeline, debug)
#
#         out = llm_rewrite(user_text, text, facts if facts else [text], sources)
#         if debug:
#             if pipeline == "RAG":
#                 return out + _render_pipeline_tag("RAG+LLM", debug)
#             return out + _render_pipeline_tag(pipeline, debug)
#         return out
#
#     if sources:
#         return (text + "\nSources: " + ", ".join(sources)) + _render_pipeline_tag(pipeline, debug)
#
#     return text + _render_pipeline_tag(pipeline, debug)
#
#
# def main():
#     full_rows = load_full_rows()
#     rag = RAGEngine(full_rows)
#
#     state: Dict[str, Any] = {
#         "last_model": None,
#         "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
#         "pending_compare": {"awaiting": False, "base_model_norm": None},
#         "slot_fill_active": False,
#         "slot_fill_missing": [],
#         "last_reco": None,
#     }
#
#     use_llm = True
#     rewrite_csv = True
#     debug = True
#
#     print("Car Assistant (CSV-first + Compare + RAG fallback + optional LLM rewrite)")
#     print("Commands: /debug on | /debug off | /reset | exit\n")
#
#     while True:
#         user = input("You: ").strip()
#         if user.lower() in {"exit", "quit"}:
#             break
#
#         if user.lower().strip() == "/debug on":
#             debug = True
#             print("\nBot: Debug ON\n")
#             continue
#         if user.lower().strip() == "/debug off":
#             debug = False
#             print("\nBot: Debug OFF\n")
#             continue
#
#         res = chat_turn(user, state, full_rows, rag, debug=debug)
#         out = render_answer(user, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)
#         print(f"\nBot: {out}\n")
#
#
# if __name__ == "__main__":
#     main()
# Good

# Update response for Cambodian styles
# scripts/chat_assistant.py
# from __future__ import annotations
#
# from typing import Dict, Any, List, Optional, Set
# import re
# import sys
# from pathlib import Path
#
# # Ensure project root is on sys.path so `from scripts...` works when running directly
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))
#
# from scripts.csv_engine import (
#     load_full_rows,
#     detect_feature_key,
#     detect_model_in_text,
#     detect_models_in_text,
#     resolve_target_model,
#     answer_feature_from_csv,
#     is_recommendation_intent,
#     extract_budget,
#     extract_seats,
#     extract_fuel,
#     extract_body_type,
#     filter_cars_split,
#     build_reco_answer,
#     is_summary_intent,
#     answer_summary_from_csv,
#     is_spec_intent,
#     answer_specs_from_csv,
#     find_row_by_model,
#     format_price_usd,
#     list_variants_for_model,
# )
# from scripts.llm_client import llm_rewrite
# from scripts.rag_engine import RAGEngine
#
#
# # ---------------- helpers ----------------
#
# def _is_small_talk(text: str) -> bool:
#     t = (text or "").strip().lower()
#     return t in {"hi", "hello", "hey", "hii", "hallo", "thanks", "thank you"} or t.startswith(
#         ("hi ", "hello ", "hey ", "thanks ", "thank you ")
#     )
#
#
# def _is_color_question(text: str) -> bool:
#     t = (text or "").strip().lower()
#     return bool(re.search(r"\b(colou?r|colors?|paint)\b", t))
#
#
# def _pipe(res: Dict[str, Any], pipeline: str, debug: bool) -> Dict[str, Any]:
#     if debug:
#         res = dict(res)
#         res["pipeline"] = pipeline
#     return res
#
#
# def _render_pipeline_tag(pipeline: str, debug: bool) -> str:
#     if not debug or not pipeline:
#         return ""
#     return f"\n[PIPELINE={pipeline}]"
#
#
# def _cancel_reco_flow(state: Dict[str, Any]) -> None:
#     state["slot_fill_active"] = False
#     state["slot_fill_missing"] = []
#     state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
#
#
# def _reset_state(state: Dict[str, Any]) -> None:
#     state.clear()
#     state.update(
#         {
#             "last_model": None,
#             "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
#             "pending_compare": {"awaiting": False, "base_model_norm": None},
#             "slot_fill_active": False,
#             "slot_fill_missing": [],
#             "last_reco": None,
#         }
#     )
#
#
# def _missing_reco_slots(slots: Dict[str, Any]) -> List[str]:
#     missing: List[str] = []
#     if slots.get("max_budget") is None:
#         missing.append("budget (USD)")
#     if not slots.get("body_type"):
#         missing.append("body type (SUV / Sedan / Pickup / MPV / Bus)")
#     if not slots.get("fuel"):
#         missing.append("fuel (Gasoline / Diesel / Hybrid / EV)")
#     return missing
#
#
# def _compare_models_from_csv(full_rows, model_a_norm: str, model_b_norm: str) -> Optional[Dict[str, Any]]:
#     row_a = find_row_by_model(full_rows, model_a_norm)
#     row_b = find_row_by_model(full_rows, model_b_norm)
#     if not row_a or not row_b:
#         return None
#
#     a_name = row_a.get("model") or model_a_norm
#     b_name = row_b.get("model") or model_b_norm
#     src_a = row_a.get("url") or ""
#     src_b = row_b.get("url") or ""
#
#     compare_fields = [
#         ("Price (USD)", "price_usd", "price"),
#         ("Body type", "body_type", None),
#         ("Seats", "seats", None),
#         ("Fuel", "fuel", None),
#         ("Minimum turning radius", "spec_minimum_turning_radius_tire", None),
#         ("Apple CarPlay / Android Auto", "spec_apple_carplay_and_android_auto", None),
#         ("Reverse camera", "spec_reverse_camera", None),
#         ("Panoramic View Monitor (PVM)", "spec_panoramic_view_monitor_pvm", None),
#         ("Blind Spot Monitor (BSM)", "spec_blind_spot_monitor_bsm", None),
#         ("Cruise control", "spec_cruise_control", None),
#         ("Wireless charging", "spec_wireless_charging", None),
#     ]
#
#     diffs: List[str] = []
#     same: List[str] = []
#
#     for label, col, kind in compare_fields:
#         av = row_a.get(col)
#         bv = row_b.get(col)
#
#         if kind == "price":
#             a_txt = format_price_usd(av)
#             b_txt = format_price_usd(bv)
#         else:
#             a_txt = str(av).strip() if av not in (None, "") else "N/A"
#             b_txt = str(bv).strip() if bv not in (None, "") else "N/A"
#
#         line = f"- {label}: {a_txt} vs {b_txt}"
#         if a_txt.strip().lower() == b_txt.strip().lower():
#             same.append(line)
#         else:
#             diffs.append(line)
#
#     lines: List[str] = []
#     lines.append("Here’s a quick comparison (official specs):")
#     lines.append(f"{a_name} vs {b_name}")
#
#     if diffs:
#         lines.append("")
#         lines.append("Key differences:")
#         lines.extend(diffs)
#
#     if same:
#         lines.append("")
#         lines.append("Same on both models:")
#         lines.extend(same)
#
#     sources: List[str] = []
#     if src_a:
#         sources.append(src_a)
#     if src_b and src_b not in sources:
#         sources.append(src_b)
#
#     text = "\n".join(lines).strip()
#     return {"answer_type": "csv_compare", "text": text, "facts": [text], "sources": sources}
#
#
# def _dataset_model_names(full_rows) -> Set[str]:
#     names: Set[str] = set()
#     for r in full_rows:
#         m = (r.get("model") or "").strip()
#         if m:
#             names.add(m.lower())
#     return names
#
# def _is_maintenance_cost_question(text: str) -> bool:
#     t = (text or "").strip().lower()
#     # If you want broader: add "service cost", "repair cost", "parts cost"
#     return ("maintenance" in t) and ("cost" in t or "price" in t or "fee" in t)
#
# def _contains_unknown_model_in_question(user_text: str, full_rows) -> Optional[str]:
#     """
#     Detect common Toyota model names not in dataset (prevents recommendation flow from leaking).
#     """
#     if not user_text:
#         return None
#
#     dataset = _dataset_model_names(full_rows)
#     leak_candidates = [
#         "rav4", "camry", "prius", "highlander", "4runner", "alphard", "voxy", "noah",
#         "c-hr", "bz4x", "sienta"
#     ]
#
#     t = user_text.lower()
#     for c in leak_candidates:
#         if re.search(rf"\b{re.escape(c)}\b", t):
#             if not any(c in name for name in dataset):
#                 return c
#     return None
#
# def _contains_out_of_dataset_model(answer_text: str, full_rows) -> Optional[str]:
#     """
#     If answer mentions a well-known Toyota model not present in CSV, block it.
#     This is a simple heuristic for common leaks (RAV4, Camry, Prius, etc.).
#     """
#     if not answer_text:
#         return None
#
#     dataset = _dataset_model_names(full_rows)
#
#     # Common leak candidates (extend any time you see a new leak)
#     leak_candidates = [
#         "rav4", "camry", "prius", "hilander", "highlander", "4runner", "corolla altis",
#         "alphard", "voxy", "noah", "c-hr", "bz4x", "aygo", "sienta",
#     ]
#
#     t = answer_text.lower()
#     for c in leak_candidates:
#         if re.search(rf"\b{re.escape(c)}\b", t):
#             # If dataset has that exact model name, allow; otherwise block.
#             # (Most of your dataset model names are longer, but RAV4 would still not appear.)
#             if not any(c in name for name in dataset):
#                 return c
#
#     return None
#
#
# # ---------------- main chat ----------------
#
# def chat_turn(user_text: str, state: Dict[str, Any], full_rows, rag: RAGEngine, debug: bool) -> Dict[str, Any]:
#     user_text = (user_text or "").strip()
#     if not user_text:
#         return _pipe({"answer_type": "system", "text": "Please type a question.", "facts": [], "sources": []}, "SYSTEM", debug)
#
#     if user_text.lower().strip() == "/reset":
#         _reset_state(state)
#         return _pipe({"answer_type": "system", "text": "Reset done.", "facts": [], "sources": []}, "SYSTEM", debug)
#
#     if _is_small_talk(user_text):
#         return _pipe(
#             {"answer_type": "system", "text": "Hi! Ask me about Toyota price, specs, features, compare, or recommendation.", "facts": [], "sources": []},
#             "SYSTEM",
#             debug,
#         )
#     # A) Block unknown models BEFORE any recommendation / csv feature routes
#     unknown = _contains_unknown_model_in_question(user_text, full_rows)
#     if unknown:
#         text = (
#             f"I don’t have '{unknown}' in my official dataset, so I can’t confirm its price/specs here.\n"
#             "Please ask about a model that exists in the dataset (example: Yaris Cross HEV, Corolla Cross HEV, Fortuner Legender, Hilux Revo, Vios, Wigo, Raize...)."
#         )
#         _cancel_reco_flow(state)
#         return _pipe({"answer_type": "system", "text": text, "facts": [], "sources": []}, "SYSTEM", debug)
#
#     # B) Maintenance cost is NOT in CSV → force RAG (avoid 'cost' becoming 'price')
#     if _is_maintenance_cost_question(user_text):
#         _cancel_reco_flow(state)
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#
#         rag_res = rag.rag_answer(user_text, last_model_norm=state.get("last_model"))
#
#         # If RAG is unsure, respond safely
#         if not (rag_res.get("text") or "").strip():
#             safe = (
#                 "Maintenance cost is not available in my official CSV specs dataset.\n"
#                 "If you want, tell me: (1) model variant, (2) year, (3) service interval you want (e.g., 10,000 km), and I’ll answer based on general guidance."
#             )
#             return _pipe({"answer_type": "system", "text": safe, "facts": [], "sources": []}, "SYSTEM", debug)
#
#         # Also block model leaks in RAG output
#         leak = _contains_out_of_dataset_model((rag_res.get("text") or ""), full_rows)
#         if leak:
#             safe = (
#                 "I can only answer using the Toyota models available in my official dataset.\n"
#                 f"I cannot confirm information about '{leak}' because it is not in the dataset."
#             )
#             return _pipe({"answer_type": "system", "text": safe, "facts": [], "sources": []}, "SYSTEM", debug)
#
#         return _pipe(rag_res, "RAG", debug)
#
#     feature_key_now = detect_feature_key(user_text)
#     spec_now = is_spec_intent(user_text)
#     summary_now = is_summary_intent(user_text)
#
#     # If user asks "colors", route to RAG (colors usually not in CSV).
#     # Also cancel slot fill to avoid budget/body prompt loop.
#     if _is_color_question(user_text):
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#         _cancel_reco_flow(state)
#         rag_res = rag.rag_answer(user_text, last_model_norm=state.get("last_model"))
#         leak = _contains_out_of_dataset_model((rag_res.get("text") or ""), full_rows)
#         if leak:
#             safe_text = (
#                 "I can only answer using the Toyota models available in my official dataset. "
#                 f"I cannot confirm information about '{leak}' because it is not in the dataset.\n"
#                 "Please ask about a model that exists in the dataset (example: Yaris Cross HEV, Corolla Cross HEV, Fortuner Legender, Hilux Revo...)."
#             )
#             return _pipe({"answer_type": "system", "text": safe_text, "facts": [], "sources": []}, "SYSTEM", debug)
#         return _pipe(rag_res, "RAG", debug)
#
#     # If slot filling is active but user asks a real Q, cancel slot filling.
#     if state.get("slot_fill_active") is True:
#         if spec_now or summary_now or feature_key_now or (" vs " in user_text.lower()) or user_text.lower().startswith("compare"):
#             _cancel_reco_flow(state)
#
#     # Fuel-only follow-up like: "diesel?" / "hybrid?" / "hev?"
#     short = user_text.lower().rstrip("?").strip()
#     if short in {"diesel", "gasoline", "hybrid", "hev", "ev", "electric"} and state.get("last_model"):
#         row = find_row_by_model(full_rows, state["last_model"])
#         if row:
#             fuel = (row.get("fuel") or "").lower().strip()
#             model_name = row.get("model") or state["last_model"]
#             short_norm = "hybrid" if short == "hev" else ("ev" if short == "electric" else short)
#
#             if fuel == short_norm:
#                 text = f"Yes — {model_name} uses {fuel} fuel (official)."
#             else:
#                 text = f"No — {model_name} is {fuel}, not {short_norm} (official)."
#
#             return _pipe(
#                 {"answer_type": "csv_feature", "text": text, "facts": [text], "sources": [row.get("url")] if row.get("url") else []},
#                 "CSV_METHOD",
#                 debug,
#             )
#
#     # "how about ..." variant listing
#     if user_text.lower().startswith(("how about", "what about")) and state.get("last_model"):
#         variants = list_variants_for_model(full_rows, state["last_model"])
#         if len(variants) > 1:
#             lines: List[str] = ["Available variants:"]
#             sources: List[str] = []
#             for v in variants:
#                 lines.append(f"- {v['model']} ({v.get('fuel','')}, {format_price_usd(v.get('price_usd'))})")
#                 if v.get("url"):
#                     sources.append(v["url"])
#             text = "\n".join(lines).strip()
#             _cancel_reco_flow(state)
#             return _pipe({"answer_type": "csv_feature", "text": text, "facts": [text], "sources": sources}, "CSV_METHOD", debug)
#
#     # Specs intent
#     if spec_now:
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#             res = answer_specs_from_csv(full_rows, model_norm)
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#
#         return _pipe(
#             {"answer_type": "system", "text": "Which Toyota model do you want specs for? Example: spec of Vios", "facts": [], "sources": []},
#             "SYSTEM",
#             debug,
#         )
#
#     # Summary intent
#     if summary_now:
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#             res = answer_summary_from_csv(full_rows, model_norm)
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#
#     # Price multi-model
#     if feature_key_now == "price":
#         models = detect_models_in_text(user_text, full_rows, max_models=3)
#         if models:
#             lines: List[str] = []
#             sources: List[str] = []
#             for m in models:
#                 res = answer_feature_from_csv(full_rows, m, "price")
#                 if res:
#                     lines.append(res["text"])
#                     for s in res.get("sources", []):
#                         if s and s not in sources:
#                             sources.append(s)
#
#             if lines:
#                 _cancel_reco_flow(state)
#                 return _pipe(
#                     {"answer_type": "csv_feature_multi", "text": "\n".join(lines), "facts": lines, "sources": sources},
#                     "CSV_METHOD",
#                     debug,
#                 )
#
#     # Other feature question
#     if feature_key_now:
#         model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
#         if model_norm:
#             state["last_model"] = model_norm
#             res = answer_feature_from_csv(full_rows, model_norm, feature_key_now)
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#
#     # Compare
#     t_norm = user_text.lower().strip()
#     if t_norm.startswith("compare") or " vs " in t_norm or " versus " in t_norm:
#         models = detect_models_in_text(user_text, full_rows, max_models=2)
#         if len(models) >= 2:
#             res = _compare_models_from_csv(full_rows, models[0], models[1])
#             if res:
#                 _cancel_reco_flow(state)
#                 return _pipe(res, "CSV_METHOD", debug)
#         return _pipe(
#             {"answer_type": "system", "text": "Which two models do you want to compare? Example: compare yaris cross and corolla cross", "facts": [], "sources": []},
#             "SYSTEM",
#             debug,
#         )
#
#     # Slot filling step (user gives missing info)
#     if state.get("slot_fill_active") is True:
#         b = extract_budget(user_text)
#         s = extract_seats(user_text)
#         f = extract_fuel(user_text)
#         bt = extract_body_type(user_text)
#
#         if b is not None:
#             state["slots"]["max_budget"] = b
#         if s is not None:
#             state["slots"]["min_seats"] = s
#         if f is not None:
#             state["slots"]["fuel"] = f
#         if bt is not None:
#             state["slots"]["body_type"] = bt
#
#         missing = _missing_reco_slots(state["slots"])
#         if missing:
#             text = "Please provide:\n" + "\n".join(f"- {m}" for m in missing) + "\n(Seats is optional)"
#             return _pipe({"answer_type": "system", "text": text, "facts": [], "sources": []}, "SYSTEM", debug)
#
#         max_budget = int(state["slots"]["max_budget"])
#         min_seats = int(state["slots"]["min_seats"] or 5)
#         fuel = state["slots"]["fuel"]
#         body_type = state["slots"]["body_type"]
#
#         verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
#         ans = build_reco_answer(verified, possible, max_items=5, assumed_seats=None if state["slots"]["min_seats"] else 5)
#
#         state["last_reco"] = {"max_budget": max_budget, "min_seats": min_seats, "fuel": fuel, "body_type": body_type}
#         _cancel_reco_flow(state)
#         return _pipe(ans, "CSV_METHOD", debug)
#
#     # Recommendation intent
#     if is_recommendation_intent(user_text) and not feature_key_now and not spec_now and not summary_now:
#         state["slots"]["max_budget"] = extract_budget(user_text)
#         state["slots"]["min_seats"] = extract_seats(user_text)
#         state["slots"]["fuel"] = extract_fuel(user_text)
#         state["slots"]["body_type"] = extract_body_type(user_text)
#
#         missing = _missing_reco_slots(state["slots"])
#         if missing:
#             text = "To recommend from official data, please tell me:\n" + "\n".join(f"- {m}" for m in missing) + "\n(Seats is optional)"
#             state["slot_fill_active"] = True
#             state["slot_fill_missing"] = missing
#             return _pipe({"answer_type": "system", "text": text, "facts": [], "sources": []}, "SYSTEM", debug)
#
#         max_budget = int(state["slots"]["max_budget"])
#         min_seats = int(state["slots"]["min_seats"] or 5)
#         fuel = state["slots"]["fuel"]
#         body_type = state["slots"]["body_type"]
#
#         verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
#         ans = build_reco_answer(verified, possible, max_items=5, assumed_seats=None if state["slots"]["min_seats"] else 5)
#
#         state["last_reco"] = {"max_budget": max_budget, "min_seats": min_seats, "fuel": fuel, "body_type": body_type}
#         _cancel_reco_flow(state)
#         return _pipe(ans, "CSV_METHOD", debug)
#
#     # Track last mentioned model
#     mentioned_model = detect_model_in_text(user_text, full_rows)
#     if mentioned_model:
#         state["last_model"] = mentioned_model
#
#     # Fallback to RAG (with leakage guard)
#     rag_res = rag.rag_answer(user_text, last_model_norm=state.get("last_model"))
#     leak = _contains_out_of_dataset_model((rag_res.get("text") or ""), full_rows)
#     if leak:
#         safe_text = (
#             "I can only answer using the Toyota models available in my official dataset. "
#             f"I cannot confirm information about '{leak}' because it is not in the dataset.\n"
#             "Please ask about a model that exists in the dataset (example: Yaris Cross HEV, Corolla Cross HEV, Fortuner Legender, Hilux Revo...)."
#         )
#         return _pipe({"answer_type": "system", "text": safe_text, "facts": [], "sources": []}, "SYSTEM", debug)
#
#     return _pipe(rag_res, "RAG", debug)
#
#
# # ---------------- render ----------------
#
# def render_answer(user_text: str, res: Dict[str, Any], use_llm: bool, rewrite_csv: bool, debug: bool) -> str:
#     """
#     SAFETY RULE:
#     - Never LLM-rewrite CSV_METHOD or SYSTEM outputs (prevents hallucination/leaks).
#     - LLM rewrite is allowed ONLY for RAG outputs.
#     """
#     text = (res.get("text") or "").strip()
#     facts = res.get("facts") or []
#     sources = res.get("sources") or []
#     pipeline = res.get("pipeline") or ""
#
#     if not text:
#         text = "I couldn't produce an answer."
#
#     # Only allow LLM rewrite for RAG
#     if use_llm and pipeline == "RAG":
#         out = llm_rewrite(user_text, text, facts or [text], sources)
#     else:
#         out = text
#
#     if sources:
#         srcs = ", ".join(s for s in sources if s)
#         if srcs:
#             out += "\nSources: " + srcs
#
#     return out + _render_pipeline_tag(pipeline, debug)
#
#
# def main() -> None:
#     full_rows = load_full_rows()
#     rag = RAGEngine(full_rows)
#
#     state: Dict[str, Any] = {}
#     _reset_state(state)
#
#     # Keep LLM ON, but rewrite only RAG (see render_answer)
#     use_llm = True
#     rewrite_csv = False  # kept for compatibility (not used for CSV now)
#     debug = True
#
#     print("Car Assistant (CSV-first + RAG fallback)")
#     print("Commands: /debug on | /debug off | /reset | exit\n")
#
#     while True:
#         user = input("You: ").strip()
#         if user.lower() in {"exit", "quit"}:
#             break
#
#         if user.lower().strip() == "/debug on":
#             debug = True
#             print("\nBot: Debug ON\n")
#             continue
#         if user.lower().strip() == "/debug off":
#             debug = False
#             print("\nBot: Debug OFF\n")
#             continue
#
#         res = chat_turn(user, state, full_rows, rag, debug=debug)
#         out = render_answer(user, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)
#         print(f"\nBot: {out}\n")
#
#
# if __name__ == "__main__":
#     main()

# scripts/chat_assistant.py
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.csv_engine import (
    load_full_rows,
    detect_feature_key,
    detect_model_in_text,
    detect_models_in_text,
    resolve_target_model,
    answer_feature_from_csv,
    is_recommendation_intent,
    extract_budget,
    extract_seats,
    extract_fuel,
    extract_body_type,
    filter_cars_split,
    build_reco_answer,
    is_summary_intent,
    answer_summary_from_csv,
    is_spec_intent,
    answer_specs_from_csv,
    find_row_by_model,
    format_price_usd,
    list_variants_for_model,
)

from scripts.llm_client import llm_rewrite


class SafeRAGFallback:
    available = False

    def __init__(self, rows):
        self.rows = rows

    def rag_answer(self, user_text: str, last_model_norm: str | None = None) -> Dict[str, Any]:
        return {
            "answer_type": "system",
            "text": "This question is not answerable from the current dataset.",
            "facts": [],
            "sources": [],
        }


def build_rag_engine(rows):
    try:
        from scripts.rag_engine import RAGEngine
        eng = RAGEngine(rows)
        setattr(eng, "available", True)
        return eng
    except Exception:
        return SafeRAGFallback(rows)


def _clean_user_text(text: str) -> str:
    t = (text or "").strip()
    # remove leading numbering like "1." or "1)"
    t = re.sub(r"^\s*\d+[\.\)]\s*", "", t)
    return t.strip()


def _is_small_talk(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"hi", "hello", "hey", "hii", "hallo", "thanks", "thank you"} or t.startswith(
        ("hi ", "hello ", "hey ", "thanks ", "thank you ")
    )


def _pipe(res: Dict[str, Any], pipeline: str, debug: bool) -> Dict[str, Any]:
    if debug:
        res = dict(res)
        res["pipeline"] = pipeline
    return res


def _render_pipeline_tag(pipeline: str, debug: bool) -> str:
    if not debug or not pipeline:
        return ""
    return f"\n[PIPELINE={pipeline}]"


def _reset_state(state: Dict[str, Any]) -> None:
    state.clear()
    state.update(
        {
            "last_model": None,
            "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
            "slot_fill_active": False,
            "slot_fill_missing": [],
            "last_reco": None,
            "awaiting_model_for": None,  # "spec" | "summary" | "feature:<key>"
        }
    )


def _cancel_reco_flow(state: Dict[str, Any]) -> None:
    state["slot_fill_active"] = False
    state["slot_fill_missing"] = []
    state["slots"] = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}


def _missing_reco_slots(slots: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    if slots.get("max_budget") is None:
        missing.append("budget (USD)")
    if not slots.get("body_type"):
        missing.append("body type (SUV / Sedan / Pickup / MPV / Bus)")
    if not slots.get("fuel"):
        missing.append("fuel (Gasoline / Diesel / Hybrid / EV)")
    return missing


def _answer_not_in_dataset(model_text: str, debug: bool) -> Dict[str, Any]:
    text = (
        f"I don’t have '{model_text}' in my dataset, so I can’t confirm price/specs/features for it here.\n"
        "Please ask about a model that exists in the dataset."
    )
    return _pipe({"answer_type": "system", "text": text, "facts": [], "sources": []}, "SYSTEM", debug)


def _answer_field_missing(full_rows, model_norm: str, feature_key: str, debug: bool) -> Dict[str, Any]:
    row = find_row_by_model(full_rows, model_norm)
    name = row.get("model") if row else model_norm
    src = row.get("url") if row else ""
    text = f"I don't have '{feature_key}' for {name} in the current dataset."
    return _pipe(
        {"answer_type": "system", "text": text, "facts": [], "sources": [src] if src else []},
        "CSV_METHOD",
        debug,
    )


def _try_switch_variant_by_fuel(full_rows, base_model_norm: str, fuel: str) -> Optional[str]:
    if not base_model_norm or not fuel:
        return None

    fuel_norm = fuel.lower().strip()
    if fuel_norm == "hev":
        fuel_norm = "hybrid"
    if fuel_norm == "electric":
        fuel_norm = "ev"
    if fuel_norm == "her":
        fuel_norm = "hev"

    # 1) try direct detection using "model + fuel"
    variant = detect_model_in_text(f"{base_model_norm} {fuel_norm}", full_rows)
    if variant:
        return variant

    # 2) try from variants list
    variants = list_variants_for_model(full_rows, base_model_norm)
    for v in variants:
        vf = (v.get("fuel") or "").lower().strip()
        if vf == fuel_norm:
            vname = (v.get("model") or "").lower().strip()
            if vname:
                return vname

    return None


def _compare_models_from_csv(full_rows, model_a_norm: str, model_b_norm: str) -> Optional[Dict[str, Any]]:
    row_a = find_row_by_model(full_rows, model_a_norm)
    row_b = find_row_by_model(full_rows, model_b_norm)
    if not row_a or not row_b:
        return None

    a_name = row_a.get("model") or model_a_norm
    b_name = row_b.get("model") or model_b_norm

    def norm_txt(v: Any) -> str:
        if v in (None, ""):
            return "N/A"
        return str(v).strip()

    lines: List[str] = []
    lines.append(f"{a_name} vs {b_name} (dataset comparison)")

    # Keep it strict and consistent
    lines.append(f"- Price: {format_price_usd(row_a.get('price_usd'))} vs {format_price_usd(row_b.get('price_usd'))}")
    lines.append(f"- Seats: {norm_txt(row_a.get('seats'))} vs {norm_txt(row_b.get('seats'))}")
    lines.append(f"- Fuel: {norm_txt(row_a.get('fuel'))} vs {norm_txt(row_b.get('fuel'))}")
    lines.append(f"- Body type: {norm_txt(row_a.get('body_type'))} vs {norm_txt(row_b.get('body_type'))}")
    lines.append(f"- Turning radius: {norm_txt(row_a.get('spec_minimum_turning_radius_tire'))} vs {norm_txt(row_b.get('spec_minimum_turning_radius_tire'))}")
    lines.append(f"- Reverse camera: {norm_txt(row_a.get('spec_reverse_camera'))} vs {norm_txt(row_b.get('spec_reverse_camera'))}")
    lines.append(f"- BSM: {norm_txt(row_a.get('spec_blind_spot_monitor_bsm'))} vs {norm_txt(row_b.get('spec_blind_spot_monitor_bsm'))}")
    lines.append(f"- Cruise control: {norm_txt(row_a.get('spec_cruise_control'))} vs {norm_txt(row_b.get('spec_cruise_control'))}")
    lines.append(f"- Wireless charging: {norm_txt(row_a.get('spec_wireless_charging'))} vs {norm_txt(row_b.get('spec_wireless_charging'))}")

    sources: List[str] = []
    if row_a.get("url"):
        sources.append(row_a["url"])
    if row_b.get("url") and row_b["url"] not in sources:
        sources.append(row_b["url"])

    text = "\n".join(lines).strip()
    return {"answer_type": "csv_compare", "text": text, "facts": [text], "sources": sources}


def chat_turn(user_text: str, state: Dict[str, Any], full_rows, rag, debug: bool) -> Dict[str, Any]:
    user_text = _clean_user_text(user_text)
    if not user_text:
        return _pipe({"answer_type": "system", "text": "Please type a question.", "facts": [], "sources": []}, "SYSTEM", debug)

    if user_text.lower().strip() == "/reset":
        _reset_state(state)
        return _pipe({"answer_type": "system", "text": "Reset done.", "facts": [], "sources": []}, "SYSTEM", debug)

    if _is_small_talk(user_text):
        return _pipe({"answer_type": "system", "text": "Hi! Ask me about price, specs, features, compare, or recommendation.", "facts": [], "sources": []}, "SYSTEM", debug)

    # If assistant previously asked "which model?"
    if state.get("awaiting_model_for"):
        m = detect_model_in_text(user_text, full_rows)
        if m:
            purpose = state["awaiting_model_for"]
            state["awaiting_model_for"] = None
            state["last_model"] = m
            _cancel_reco_flow(state)

            if purpose == "spec":
                res = answer_specs_from_csv(full_rows, m)
                if res:
                    return _pipe(res, "CSV_METHOD", debug)
            if purpose == "summary":
                res = answer_summary_from_csv(full_rows, m)
                if res:
                    return _pipe(res, "CSV_METHOD", debug)
            if purpose.startswith("feature:"):
                fk = purpose.split(":", 1)[1]
                res = answer_feature_from_csv(full_rows, m, fk)
                if res:
                    return _pipe(res, "CSV_METHOD", debug)

            return _pipe({"answer_type": "system", "text": "I couldn't answer that from the dataset.", "facts": [], "sources": []}, "SYSTEM", debug)

    feature_key_now = detect_feature_key(user_text)
    spec_now = is_spec_intent(user_text) or bool(re.fullmatch(r"specs?\??", user_text.strip().lower()))
    summary_now = is_summary_intent(user_text)

    # If we are in slot-fill but user is asking something else, cancel slot-fill
    if state.get("slot_fill_active") is True:
        looks_like_reco = is_recommendation_intent(user_text)
        has_model = bool(detect_model_in_text(user_text, full_rows) or detect_models_in_text(user_text, full_rows, max_models=2))
        looks_like_compare = " vs " in user_text.lower() or "compare" in user_text.lower()
        looks_like_feature = bool(feature_key_now)
        looks_like_spec_summary = bool(spec_now or summary_now)

        if not looks_like_reco and (has_model or looks_like_compare or looks_like_feature or looks_like_spec_summary):
            _cancel_reco_flow(state)

    # Detect model mentions for context
    mentioned_model = detect_model_in_text(user_text, full_rows)
    if mentioned_model:
        state["last_model"] = mentioned_model

    # Fuel-only follow-up: "diesel?" / "hev?" etc
    short = user_text.lower().rstrip("?").strip()
    if short == "her":
        short = "hev"

    if short in {"diesel", "gasoline", "hybrid", "hev", "ev", "electric"} and state.get("last_model"):
        # If user is switching variant (hev/hybrid/etc), switch last_model when possible
        fuel = extract_fuel(short)
        if fuel:
            variant = _try_switch_variant_by_fuel(full_rows, state["last_model"], fuel)
            if variant:
                state["last_model"] = variant

        row = find_row_by_model(full_rows, state["last_model"])
        if row:
            fuel_row = (row.get("fuel") or "").lower().strip()
            model_name = row.get("model") or state["last_model"]

            short_norm = short
            if short_norm == "hev":
                short_norm = "hybrid"
            if short_norm == "electric":
                short_norm = "ev"

            if fuel_row == short_norm:
                text = f"Yes — {model_name} uses {fuel_row} fuel (dataset)."
            else:
                text = f"No — {model_name} is {fuel_row}, not {short_norm} (dataset)."

            return _pipe({"answer_type": "csv_feature", "text": text, "facts": [text], "sources": [row.get("url")] if row.get("url") else []}, "CSV_METHOD", debug)

    # Compare
    t_norm = user_text.lower()
    if t_norm.startswith("compare") or " vs " in t_norm or " versus " in t_norm:
        models = detect_models_in_text(user_text, full_rows, max_models=2)
        if len(models) >= 2:
            res = _compare_models_from_csv(full_rows, models[0], models[1])
            if res:
                _cancel_reco_flow(state)
                return _pipe(res, "CSV_METHOD", debug)
        return _pipe(
            {"answer_type": "system", "text": "Which two models do you want to compare? Example: compare A and B", "facts": [], "sources": []},
            "SYSTEM",
            debug,
        )

    # Specs
    if spec_now:
        model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)

        # FIX: if user says "what about the spec" and model is not detected,
        # use memory (last_model) instead of asking again
        if not model_norm and state.get("last_model"):
            model_norm = state["last_model"]

        if model_norm:
            state["last_model"] = model_norm
            _cancel_reco_flow(state)
            res = answer_specs_from_csv(full_rows, model_norm)
            if res:
                return _pipe(res, "CSV_METHOD", debug)
            return _pipe(
                {"answer_type": "system", "text": "I couldn't find specs for that model in the dataset.", "facts": [],
                 "sources": []},
                "SYSTEM",
                debug,
            )

        state["awaiting_model_for"] = "spec"
        return _pipe(
            {"answer_type": "system", "text": "Which model do you want specs for?", "facts": [], "sources": []},
            "SYSTEM", debug)

    # Summary
    if summary_now:
        model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
        if model_norm:
            state["last_model"] = model_norm
            _cancel_reco_flow(state)
            res = answer_summary_from_csv(full_rows, model_norm)
            if res:
                return _pipe(res, "CSV_METHOD", debug)
            return _pipe({"answer_type": "system", "text": "I couldn't find a summary for that model in the dataset.", "facts": [], "sources": []}, "SYSTEM", debug)

        state["awaiting_model_for"] = "summary"
        return _pipe({"answer_type": "system", "text": "Which model do you want the summary for?", "facts": [], "sources": []}, "SYSTEM", debug)

    # Price or other feature: support "price for hev?" by switching variant first
    if feature_key_now:
        fuel_in_text = extract_fuel(user_text)
        if fuel_in_text and feature_key_now == "price" and state.get("last_model"):
            variant = _try_switch_variant_by_fuel(full_rows, state["last_model"], fuel_in_text)
            if variant:
                state["last_model"] = variant

        model_norm = resolve_target_model(user_text, state.get("last_model"), full_rows)
        if model_norm:
            state["last_model"] = model_norm
            _cancel_reco_flow(state)

            res = answer_feature_from_csv(full_rows, model_norm, feature_key_now)
            if res:
                return _pipe(res, "CSV_METHOD", debug)

            # strict dataset-only response when field not available (colors, maintenance cost, etc)
            state["awaiting_model_for"] = None
            return _answer_field_missing(full_rows, model_norm, feature_key_now, debug)

        # If user asked feature but no model is known, ask for model
        state["awaiting_model_for"] = f"feature:{feature_key_now}"
        return _pipe({"answer_type": "system", "text": "Which model are you asking about?", "facts": [], "sources": []}, "SYSTEM", debug)

    # Recommendation
    if is_recommendation_intent(user_text):
        b = extract_budget(user_text)
        s = extract_seats(user_text)
        f = extract_fuel(user_text)
        bt = extract_body_type(user_text)

        if b is not None:
            state["slots"]["max_budget"] = b
        if s is not None:
            state["slots"]["min_seats"] = s
        if f is not None:
            state["slots"]["fuel"] = f
        if bt is not None:
            state["slots"]["body_type"] = bt

        missing = _missing_reco_slots(state["slots"])
        if missing:
            state["slot_fill_active"] = True
            state["slot_fill_missing"] = missing
            text = "To recommend from the dataset, please tell me:\n" + "\n".join(f"- {m}" for m in missing) + "\n(Seats is optional)"
            return _pipe({"answer_type": "system", "text": text, "facts": [], "sources": []}, "SYSTEM", debug)

        max_budget = int(state["slots"]["max_budget"])
        min_seats = int(state["slots"]["min_seats"] or 5)
        fuel = state["slots"]["fuel"]
        body_type = state["slots"]["body_type"]

        verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
        ans = build_reco_answer(verified, possible, max_items=5, assumed_seats=None if state["slots"]["min_seats"] else 5)

        state["last_reco"] = {"max_budget": max_budget, "min_seats": min_seats, "fuel": fuel, "body_type": body_type}
        _cancel_reco_flow(state)
        return _pipe(ans, "CSV_METHOD", debug)

    # Slot filling continuation
    if state.get("slot_fill_active") is True:
        b = extract_budget(user_text)
        s = extract_seats(user_text)
        f = extract_fuel(user_text)
        bt = extract_body_type(user_text)

        if b is not None:
            state["slots"]["max_budget"] = b
        if s is not None:
            state["slots"]["min_seats"] = s
        if f is not None:
            state["slots"]["fuel"] = f
        if bt is not None:
            state["slots"]["body_type"] = bt

        missing = _missing_reco_slots(state["slots"])
        if missing:
            text = "Please provide:\n" + "\n".join(f"- {m}" for m in missing) + "\n(Seats is optional)"
            return _pipe({"answer_type": "system", "text": text, "facts": [], "sources": []}, "SYSTEM", debug)

        max_budget = int(state["slots"]["max_budget"])
        min_seats = int(state["slots"]["min_seats"] or 5)
        fuel = state["slots"]["fuel"]
        body_type = state["slots"]["body_type"]

        verified, possible = filter_cars_split(full_rows, max_budget, min_seats, fuel, body_type)
        ans = build_reco_answer(verified, possible, max_items=5, assumed_seats=None if state["slots"]["min_seats"] else 5)

        state["last_reco"] = {"max_budget": max_budget, "min_seats": min_seats, "fuel": fuel, "body_type": body_type}
        _cancel_reco_flow(state)
        return _pipe(ans, "CSV_METHOD", debug)

    # Fallback (RAG if available, otherwise strict CSV-only)
    pipeline = "RAG" if getattr(rag, "available", False) else "CSV_ONLY"
    return _pipe(rag.rag_answer(user_text, last_model_norm=state.get("last_model")), pipeline, debug)


def render_answer(user_text: str, res: Dict[str, Any], use_llm: bool, rewrite_csv: bool, debug: bool) -> str:
    text = (res.get("text") or "").strip()
    facts = res.get("facts") or []
    sources = res.get("sources") or []
    pipeline = res.get("pipeline") or ""

    if not text:
        text = "I couldn't produce an answer."

    if use_llm:
        # For demo safety: keep CSV answers exact by setting rewrite_csv=False
        if pipeline == "CSV_METHOD" and not rewrite_csv:
            out = text
        else:
            ground = facts if facts else [text]
            out = llm_rewrite(user_text, text, ground, sources)
    else:
        out = text

    if sources:
        srcs = ", ".join(s for s in sources if s)
        if srcs:
            out += "\nSources: " + srcs

    return out + _render_pipeline_tag(pipeline, debug)


def main() -> None:
    full_rows = load_full_rows()
    rag = build_rag_engine(full_rows)

    state: Dict[str, Any] = {}
    _reset_state(state)

    use_llm = True
    rewrite_csv = False  # recommended for demo (keeps dataset answers strict)
    debug = True

    print("Assistant (CSV-first + optional RAG fallback)")
    print("Commands: /debug on | /debug off | /reset | exit\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break

        if user.lower().strip() == "/debug on":
            debug = True
            print("\nBot: Debug ON\n")
            continue
        if user.lower().strip() == "/debug off":
            debug = False
            print("\nBot: Debug OFF\n")
            continue

        res = chat_turn(user, state, full_rows, rag, debug=debug)
        out = render_answer(user, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)
        print(f"\nBot: {out}\n")


if __name__ == "__main__":
    main()