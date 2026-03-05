# # # scripts/app.py
# # from __future__ import annotations
# #
# # import sys
# # from pathlib import Path
# # from typing import Dict, Any
# #
# # import streamlit as st
# #
# # PROJECT_ROOT = Path(__file__).resolve().parents[1]
# # if str(PROJECT_ROOT) not in sys.path:
# #     sys.path.insert(0, str(PROJECT_ROOT))
# #
# # from scripts.csv_engine import load_full_rows
# # from scripts.chat_assistant import chat_turn, render_answer, build_rag_engine
# #
# #
# # def init_state() -> Dict[str, Any]:
# #     return {
# #         "last_model": None,
# #         "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
# #         "pending_compare": {"awaiting": False, "base_model_norm": None},
# #         "slot_fill_active": False,
# #         "slot_fill_missing": [],
# #         "last_reco": None,
# #     }
# #
# #
# # @st.cache_resource
# # def load_resources():
# #     rows = load_full_rows()
# #     rag = build_rag_engine(rows)  # safe fallback when chromadb missing
# #     backend_mode = "RAG" if rag.__class__.__name__ != "SafeRAGFallback" else "CSV_ONLY"
# #     return rows, rag, backend_mode
# #
# #
# # def strip_sources(text: str) -> str:
# #     return text.split("\nSources:", 1)[0].strip()
# #
# #
# # st.set_page_config(page_title="Assistant", layout="wide")
# #
# # full_rows, rag, backend_mode = load_resources()
# #
# # if "bot_state" not in st.session_state:
# #     st.session_state.bot_state = init_state()
# #
# # if "messages" not in st.session_state:
# #     st.session_state.messages = []
# #
# # with st.sidebar:
# #     st.title("Controls")
# #     st.caption(f"Backend: {backend_mode}")
# #
# #     show_sources = st.toggle("Show sources", value=True)
# #     debug = st.toggle("Debug (show pipeline)", value=True)
# #     use_llm = st.toggle("LLM rewrite", value=True)
# #     rewrite_csv = st.toggle("Rewrite CSV answers", value=True)
# #
# #     if st.button("Reset conversation"):
# #         st.session_state.bot_state = init_state()
# #         st.session_state.messages = []
# #         st.rerun()
# #
# # st.markdown("## Assistant (same logic as console)")
# #
# # for msg in st.session_state.messages:
# #     with st.chat_message(msg["role"]):
# #         st.write(msg["content"])
# #
# # user_input = st.chat_input("Type your question...")
# # if user_input:
# #     res = chat_turn(user_input, st.session_state.bot_state, full_rows, rag, debug=debug)
# #     out = render_answer(user_input, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)
# #
# #     if not show_sources:
# #         out = strip_sources(out)
# #
# #     st.session_state.messages.append({"role": "user", "content": user_input})
# #     st.session_state.messages.append({"role": "assistant", "content": out})
# #     st.rerun()
#
# # scripts/app.py
# from __future__ import annotations
#
# import sys
# from pathlib import Path
# from typing import Dict, Any
#
# import streamlit as st
#
# # Ensure project root is on sys.path so `from scripts...` works
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))
#
# from scripts.csv_engine import load_full_rows
# from scripts.chat_assistant import chat_turn, render_answer, build_rag_engine
#
#
# def init_bot_state() -> Dict[str, Any]:
#     return {
#         "last_model": None,
#         "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
#         "slot_fill_active": False,
#         "slot_fill_missing": [],
#         "last_reco": None,
#         "awaiting_model_for": None,  # "spec" | "summary" | "feature:<key>"
#     }
#
#
# @st.cache_resource
# def load_resources():
#     # Same as console:
#     # - load_full_rows()
#     # - build_rag_engine(rows)
#     rows = load_full_rows()
#     rag = build_rag_engine(rows)
#     return rows, rag
#
#
# def strip_sources(text: str) -> str:
#     return text.split("\nSources:", 1)[0].strip()
#
#
# st.set_page_config(page_title="Assistant", layout="wide")
#
# full_rows, rag = load_resources()
#
# # Persist chat memory in Streamlit session state
# if "bot_state" not in st.session_state:
#     st.session_state.bot_state = init_bot_state()
#
# if "messages" not in st.session_state:
#     st.session_state.messages = []
#
# with st.sidebar:
#     st.title("Controls")
#
#     backend = "RAG" if getattr(rag, "available", False) else "CSV_ONLY"
#     st.caption(f"Backend: {backend}")
#
#     # Keep defaults aligned with console safety:
#     show_sources = st.toggle("Show sources", value=True)
#     debug = st.toggle("Debug (show pipeline)", value=True)
#
#     # LLM rewrite settings:
#     use_llm = st.toggle("LLM rewrite", value=True)
#
#     # IMPORTANT: to match console behavior and prevent “made-up” values,
#     # keep CSV answers strict (no rewrite).
#     rewrite_csv = st.toggle("Rewrite CSV answers", value=False)
#
#     if st.button("Reset conversation"):
#         st.session_state.bot_state = init_bot_state()
#         st.session_state.messages = []
#         st.rerun()
#
# st.markdown("## Assistant (same logic as console)")
#
# # Render chat history
# for msg in st.session_state.messages:
#     with st.chat_message(msg["role"]):
#         st.write(msg["content"])
#
# # Input
# user_input = st.chat_input("Type your question...")
# if user_input:
#     res = chat_turn(user_input, st.session_state.bot_state, full_rows, rag, debug=debug)
#     out = render_answer(user_input, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)
#
#     if not show_sources:
#         out = strip_sources(out)
#
#     st.session_state.messages.append({"role": "user", "content": user_input})
#     st.session_state.messages.append({"role": "assistant", "content": out})
#     st.rerun()

# scripts/app.py
# # GUI Version 2
# from __future__ import annotations
#
# import re
# import sys
# from pathlib import Path
# from typing import Dict, Any, List, Tuple
#
# import streamlit as st
#
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))
#
# from scripts.csv_engine import load_full_rows
# from scripts.chat_assistant import chat_turn, render_answer, build_rag_engine
#
#
# APP_TITLE = "Knowledge-Grounded Assistant"
# APP_SUBTITLE = "Structured filtering + Dataset QA + RAG fallback (same logic as console)"
#
#
# def _strip_sources_block(text: str) -> Tuple[str, List[str]]:
#     """
#     Split:
#       main_text
#       Sources: url1, url2
#     into main_text + list of sources.
#     """
#     if not text:
#         return "", []
#     parts = text.split("\nSources:", 1)
#     main = parts[0].strip()
#     if len(parts) == 1:
#         return main, []
#     srcs = parts[1].strip()
#     if not srcs:
#         return main, []
#     urls = [s.strip() for s in srcs.split(",") if s.strip()]
#     return main, urls
#
#
# def _strip_pipeline_tag(text: str) -> Tuple[str, str]:
#     """
#     Extract [PIPELINE=...] tag if present at end.
#     """
#     if not text:
#         return "", ""
#     m = re.search(r"\[PIPELINE=([^\]]+)\]\s*$", text.strip())
#     if not m:
#         return text.strip(), ""
#     pipeline = m.group(1).strip()
#     clean = re.sub(r"\s*\[PIPELINE=[^\]]+\]\s*$", "", text.strip()).strip()
#     return clean, pipeline
#
#
# def _init_bot_state() -> Dict[str, Any]:
#     return {
#         "last_model": None,
#         "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
#         "slot_fill_active": False,
#         "slot_fill_missing": [],
#         "last_reco": None,
#         "awaiting_model_for": None,
#     }
#
#
# @st.cache_resource
# def _load_resources():
#     rows = load_full_rows()
#     rag = build_rag_engine(rows)
#     return rows, rag
#
#
# def _apply_ui_css():
#     st.markdown(
#         """
# <style>
# /* Layout */
# .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }
#
# /* Header */
# .app-title { font-size: 28px; font-weight: 700; margin: 0; }
# .app-subtitle { font-size: 14px; opacity: 0.75; margin-top: 4px; }
#
# /* Chat bubbles */
# .msg-wrap { padding: 12px 14px; border-radius: 14px; border: 1px solid rgba(120,120,120,0.25); }
# .msg-user { background: rgba(120,120,120,0.08); }
# .msg-assistant { background: rgba(40,120,255,0.06); }
#
# /* Badges */
# .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 12px; border: 1px solid rgba(120,120,120,0.30); }
# .badge-ok { background: rgba(16,185,129,0.10); }
# .badge-warn { background: rgba(245,158,11,0.10); }
# .badge-info { background: rgba(59,130,246,0.10); }
#
# /* Small helper text */
# .hint { font-size: 12px; opacity: 0.75; margin-top: 6px; }
#
# /* Cards */
# .card { border: 1px solid rgba(120,120,120,0.25); border-radius: 16px; padding: 14px 14px; }
# .card h3 { margin: 0 0 6px 0; font-size: 16px; }
# </style>
#         """,
#         unsafe_allow_html=True,
#     )
#
#
# def _render_header(rag_available: bool):
#     left, right = st.columns([3, 1], vertical_alignment="center")
#     with left:
#         st.markdown(f"<p class='app-title'>{APP_TITLE}</p>", unsafe_allow_html=True)
#         st.markdown(f"<p class='app-subtitle'>{APP_SUBTITLE}</p>", unsafe_allow_html=True)
#     with right:
#         if rag_available:
#             st.markdown("<span class='badge badge-ok'>RAG: Ready</span>", unsafe_allow_html=True)
#         else:
#             st.markdown("<span class='badge badge-warn'>RAG: Disabled</span>", unsafe_allow_html=True)
#
#
# def _render_message(role: str, content: str):
#     clean, pipeline = _strip_pipeline_tag(content)
#     main, sources = _strip_sources_block(clean)
#
#     if role == "user":
#         st.markdown(f"<div class='msg-wrap msg-user'><b>You</b><br/>{main}</div>", unsafe_allow_html=True)
#         return
#
#     badge_html = ""
#     if pipeline:
#         if pipeline.upper().startswith("CSV"):
#             badge_html = "<span class='badge badge-ok'>CSV_METHOD</span>"
#         elif "RAG" in pipeline.upper():
#             badge_html = "<span class='badge badge-info'>RAG</span>"
#         else:
#             badge_html = "<span class='badge badge-warn'>SYSTEM</span>"
#
#     st.markdown(
#         f"<div class='msg-wrap msg-assistant'><b>Assistant</b> {badge_html}<br/>{main}</div>",
#         unsafe_allow_html=True,
#     )
#
#     if sources:
#         with st.expander("Sources", expanded=False):
#             for u in sources:
#                 st.write(u)
#
#
# def _run_turn(
#     user_text: str,
#     full_rows,
#     rag,
#     bot_state: Dict[str, Any],
#     use_llm: bool,
#     rewrite_csv: bool,
#     debug: bool,
#     show_sources: bool,
# ) -> str:
#     res = chat_turn(user_text, bot_state, full_rows, rag, debug=debug)
#     out = render_answer(user_text, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)
#
#     if not show_sources:
#         out_clean, _ = _strip_pipeline_tag(out)
#         out_main, _ = _strip_sources_block(out_clean)
#         pipeline = res.get("pipeline") if debug else ""
#         if debug and pipeline:
#             out = out_main + f"\n[PIPELINE={pipeline}]"
#         else:
#             out = out_main
#     return out
#
#
# def _inspector_panel(bot_state: Dict[str, Any], rag_available: bool):
#     st.markdown("<div class='card'>", unsafe_allow_html=True)
#     st.markdown("<h3>Inspector</h3>", unsafe_allow_html=True)
#
#     st.write("Runtime")
#     st.write(f"- RAG available: {rag_available}")
#     st.write("")
#
#     st.write("Conversation memory")
#     st.write(f"- last_model: {bot_state.get('last_model')}")
#     slots = bot_state.get("slots", {})
#     st.write("- slots:")
#     st.write(f"  - max_budget: {slots.get('max_budget')}")
#     st.write(f"  - min_seats: {slots.get('min_seats')}")
#     st.write(f"  - fuel: {slots.get('fuel')}")
#     st.write(f"  - body_type: {slots.get('body_type')}")
#     st.write(f"- slot_fill_active: {bot_state.get('slot_fill_active')}")
#     st.write(f"- awaiting_model_for: {bot_state.get('awaiting_model_for')}")
#
#     st.markdown("</div>", unsafe_allow_html=True)
#
#
# def _get_models(full_rows) -> List[str]:
#     models = sorted({(r.get("model") or "").strip() for r in full_rows if r.get("model")})
#     return [m for m in models if m]
#
#
# def main():
#     st.set_page_config(page_title=APP_TITLE, layout="wide")
#     _apply_ui_css()
#
#     full_rows, rag = _load_resources()
#     rag_available = bool(getattr(rag, "available", False))
#
#     if "bot_state" not in st.session_state:
#         st.session_state.bot_state = _init_bot_state()
#     if "messages" not in st.session_state:
#         st.session_state.messages = []
#
#     # Sidebar controls
#     with st.sidebar:
#         st.markdown("### Controls")
#         show_sources = st.toggle("Show sources", value=True)
#         debug = st.toggle("Debug (show pipeline)", value=True)
#         use_llm = st.toggle("LLM rewrite", value=True)
#         rewrite_csv = st.toggle("Rewrite CSV answers", value=False)
#         st.caption("Tip: for strict demo, keep Rewrite CSV answers OFF.")
#         if st.button("Reset conversation"):
#             st.session_state.bot_state = _init_bot_state()
#             st.session_state.messages = []
#             st.rerun()
#
#         st.divider()
#         _inspector_panel(st.session_state.bot_state, rag_available)
#
#     # Header
#     _render_header(rag_available)
#     st.divider()
#
#     # Tabs
#     tab_chat, tab_reco, tab_compare, tab_browse, tab_demo = st.tabs(
#         ["Chat", "Recommend", "Compare", "Browse", "Demo Script"]
#     )
#
#     with tab_chat:
#         left, right = st.columns([3, 2], vertical_alignment="top")
#
#         with left:
#             st.markdown("#### Conversation")
#             for msg in st.session_state.messages:
#                 _render_message(msg["role"], msg["content"])
#
#             user_input = st.chat_input("Type your question...")
#             if user_input:
#                 out = _run_turn(
#                     user_input,
#                     full_rows,
#                     rag,
#                     st.session_state.bot_state,
#                     use_llm=use_llm,
#                     rewrite_csv=rewrite_csv,
#                     debug=debug,
#                     show_sources=show_sources,
#                 )
#                 st.session_state.messages.append({"role": "user", "content": user_input})
#                 st.session_state.messages.append({"role": "assistant", "content": out})
#                 st.rerun()
#
#         with right:
#             st.markdown("#### Suggested prompts")
#             st.markdown("<div class='hint'>Click to auto-send during demo.</div>", unsafe_allow_html=True)
#
#             suggested = [
#                 "price of vios",
#                 "spec",
#                 "diesel?",
#                 "does it have 360 camera?",
#                 "compare yaris cross and corolla cross",
#                 "recommend budget 50000 suv hybrid",
#                 "do you have rav4 hybrid",
#                 "maintenance cost of vios",
#                 "what colors are available for yaris cross hev",
#             ]
#
#             for q in suggested:
#                 if st.button(q, use_container_width=True):
#                     out = _run_turn(
#                         q,
#                         full_rows,
#                         rag,
#                         st.session_state.bot_state,
#                         use_llm=use_llm,
#                         rewrite_csv=rewrite_csv,
#                         debug=debug,
#                         show_sources=show_sources,
#                     )
#                     st.session_state.messages.append({"role": "user", "content": q})
#                     st.session_state.messages.append({"role": "assistant", "content": out})
#                     st.rerun()
#
#             st.divider()
#             st.markdown("#### Demo checklist")
#             st.write("- Start with price question")
#             st.write("- Ask 'spec' to test memory")
#             st.write("- Ask a feature question")
#             st.write("- Compare two models")
#             st.write("- Recommendation with slots")
#             st.write("- Ask a model not in dataset")
#             st.write("- Ask an unsupported field")
#
#     with tab_reco:
#         st.markdown("#### Structured recommendation")
#         c1, c2, c3, c4 = st.columns(4)
#         with c1:
#             budget = st.number_input("Max budget (USD)", min_value=0, value=50000, step=500)
#         with c2:
#             fuel = st.selectbox("Fuel", ["hybrid", "gasoline", "diesel", "ev", "any"], index=0)
#         with c3:
#             body = st.selectbox("Body type", ["suv", "sedan", "pickup", "mpv", "bus", "any"], index=0)
#         with c4:
#             seats = st.selectbox("Min seats (optional)", [None, 5, 7, 12, 16], index=1)
#
#         if st.button("Run recommendation", type="primary"):
#             parts = [f"recommend budget {int(budget)}", body, fuel]
#             if seats:
#                 parts.append(f"{seats} seats")
#             q = " ".join(parts)
#
#             out = _run_turn(
#                 q,
#                 full_rows,
#                 rag,
#                 st.session_state.bot_state,
#                 use_llm=use_llm,
#                 rewrite_csv=rewrite_csv,
#                 debug=debug,
#                 show_sources=show_sources,
#             )
#             st.session_state.messages.append({"role": "user", "content": q})
#             st.session_state.messages.append({"role": "assistant", "content": out})
#             st.success("Added to chat history. Go to Chat tab to present.")
#             st.rerun()
#
#     with tab_compare:
#         st.markdown("#### Compare two models (dataset fields only)")
#         models = _get_models(full_rows)
#         if not models:
#             st.warning("No models found in the dataset.")
#         else:
#             c1, c2 = st.columns(2)
#             with c1:
#                 a = st.selectbox("Model A", models, index=0)
#             with c2:
#                 b = st.selectbox("Model B", models, index=1 if len(models) > 1 else 0)
#
#             if st.button("Run comparison", type="primary"):
#                 q = f"compare {a} and {b}"
#                 out = _run_turn(
#                     q,
#                     full_rows,
#                     rag,
#                     st.session_state.bot_state,
#                     use_llm=use_llm,
#                     rewrite_csv=rewrite_csv,
#                     debug=debug,
#                     show_sources=show_sources,
#                 )
#                 st.session_state.messages.append({"role": "user", "content": q})
#                 st.session_state.messages.append({"role": "assistant", "content": out})
#                 st.success("Added to chat history. Go to Chat tab to present.")
#                 st.rerun()
#
#     with tab_browse:
#         st.markdown("#### Browse dataset (for reviewer trust)")
#         q = st.text_input("Search model name", "")
#         rows = []
#         for r in full_rows:
#             name = (r.get("model") or "").strip()
#             if q.strip() and q.lower() not in name.lower():
#                 continue
#             rows.append(
#                 {
#                     "model": r.get("model"),
#                     "price_usd": r.get("price_usd"),
#                     "fuel": r.get("fuel"),
#                     "body_type": r.get("body_type"),
#                     "seats": r.get("seats"),
#                     "url": r.get("url"),
#                 }
#             )
#         st.write(f"Rows: {len(rows)}")
#         st.dataframe(rows, use_container_width=True, hide_index=True)
#
#     with tab_demo:
#         st.markdown("#### One-click demo flow")
#         st.markdown("<div class='hint'>Click in order during presentation.</div>", unsafe_allow_html=True)
#
#         flow = [
#             "price of vios",
#             "spec",
#             "does it have 360 camera?",
#             "compare yaris cross and corolla cross",
#             "recommend budget 50000 suv hybrid",
#             "do you have rav4 hybrid",
#             "maintenance cost of vios",
#         ]
#
#         for step, q in enumerate(flow, start=1):
#             if st.button(f"{step}. {q}", use_container_width=True):
#                 out = _run_turn(
#                     q,
#                     full_rows,
#                     rag,
#                     st.session_state.bot_state,
#                     use_llm=use_llm,
#                     rewrite_csv=rewrite_csv,
#                     debug=debug,
#                     show_sources=show_sources,
#                 )
#                 st.session_state.messages.append({"role": "user", "content": q})
#                 st.session_state.messages.append({"role": "assistant", "content": out})
#                 st.rerun()
#
#
# if __name__ == "__main__":
#     main()
# scripts/app.py
import streamlit as st
import time
import re

from scripts.csv_engine import (
    extract_budget,
    is_recommendation_intent,
    detect_feature_key,
    is_spec_intent,
    is_summary_intent,
)
from scripts.chat_assistant import (
    load_full_rows,
    build_rag_engine,
    chat_turn,
    render_answer,
    _reset_state
)

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Assistant",
    page_icon="🚗",
    layout="centered"
)

# --- 2. DARK THEME & BRANDING (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }

    .stChatMessage {
        border-radius: 15px;
        background-color: #262730;
        border: 1px solid #333;
    }

    .stChatInputContainer { padding-bottom: 20px; background-color: transparent; }

    button[kind="primary"] {
        background-color: #eb0a1e;
        border: none;
        color: white;
    }

    h1, h2, h3, p, span { color: #FFFFFF !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. INITIALIZE DATA & ENGINE ---
@st.cache_resource
def load_resources():
    rows = load_full_rows()
    rag = build_rag_engine(rows)  # SAME builder as console
    return rows, rag

full_rows, rag = load_resources()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "logic_state" not in st.session_state:
    st.session_state.logic_state = {}
    _reset_state(st.session_state.logic_state)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("Menu")

    if st.button("🗑️ Reset Chat"):
        st.session_state.messages = []
        _reset_state(st.session_state.logic_state)
        st.rerun()

    st.divider()
    debug_mode = st.toggle("Show Logic Tags", value=False)

    # IMPORTANT: allow LLM rewrite ONLY for CSV answers
    rewrite_csv_answers = st.toggle("Make CSV answers more natural", value=True)

    st.caption("Tip: If answers become 'creative', turn off rewrite.")

# --- 5. PAGE TITLE ---
st.title("🚗 Intelligence")
st.markdown("##### *Dark Edition*")

# --- 6. RENDER HISTORY ---
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🏎️"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- Helper: make user budget sentences trigger recommendation flow ---
def normalize_user_prompt(p: str) -> str:
    t = (p or "").strip()
    low = t.lower()

    # remove leading numbering like "1." / "1)"
    t = re.sub(r"^\s*\d+[\.\)]\s*", "", t).strip()
    low = t.lower()

    # If user mentions budget + buy/want new car, but didn't say "recommend", force reco intent
    b = extract_budget(t)
    if (
        b is not None
        and not is_recommendation_intent(t)
        and not detect_feature_key(t)
        and not is_spec_intent(t)
        and not is_summary_intent(t)
        and any(k in low for k in ["buy", "want", "looking", "need", "new car", "purchase"])
    ):
        return f"recommend {t}"
    return t

# --- 7. CHAT INPUT ---
if prompt := st.chat_input("Ask about models..."):
    prompt = normalize_user_prompt(prompt)

    st.chat_message("user", avatar="👤").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar="🏎️"):
        response_placeholder = st.empty()

        # 1) Core logic (same as console)
        res = chat_turn(prompt, st.session_state.logic_state, full_rows, rag, debug=debug_mode)

        # 2) Decide when to allow LLM rewrite
        #    - Allow only for CSV answers (dataset grounded)
        #    - Never rewrite SYSTEM / CSV_ONLY fallback (prevents RAV4/colors hallucination)
        pipeline = res.get("pipeline", "")
        answer_type = (res.get("answer_type") or "").lower()
        is_csv_answer = (pipeline == "CSV_METHOD") or answer_type.startswith("csv_")

        use_llm_effective = is_csv_answer
        rewrite_csv_effective = rewrite_csv_answers  # only matters when use_llm_effective is True

        full_answer = render_answer(
            prompt,
            res,
            use_llm=use_llm_effective,
            rewrite_csv=rewrite_csv_effective,
            debug=debug_mode
        )

        # 3) Typewriter effect
        displayed_text = ""
        for word in full_answer.split(" "):
            displayed_text += word + " "
            response_placeholder.markdown(displayed_text + "▌")
            time.sleep(0.015)
        response_placeholder.markdown(full_answer)

    st.session_state.messages.append({"role": "assistant", "content": full_answer})









