# scripts/app.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, Tuple

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.csv_engine import load_full_rows
from scripts.chat_assistant import chat_turn, render_answer


class SafeRAGFallback:
    def __init__(self, rows):
        self.rows = rows

    def rag_answer(self, user_text: str, last_model_norm: str | None = None) -> Dict[str, Any]:
        return {
            "answer_type": "system",
            "text": "RAG is not available right now. I will answer using the dataset only.",
            "facts": [],
            "sources": [],
        }


def try_build_rag(rows) -> Tuple[object, str]:
    try:
        from scripts.rag_engine import RAGEngine
        return RAGEngine(rows), "RAG"
    except Exception:
        return SafeRAGFallback(rows), "CSV_ONLY"


def init_state() -> Dict[str, Any]:
    return {
        "last_model": None,
        "slots": {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None},
        "pending_compare": {"awaiting": False, "base_model_norm": None},
        "slot_fill_active": False,
        "slot_fill_missing": [],
        "last_reco": None,
    }


@st.cache_resource
def load_resources():
    rows = load_full_rows()
    rag, mode = try_build_rag(rows)
    models = sorted({(r.get("model") or "").strip() for r in rows if r.get("model")})
    return rows, rag, mode, models


def strip_sources(text: str) -> str:
    return text.split("\nSources:", 1)[0].strip()


st.set_page_config(page_title="Vehicle Assistant", layout="wide")

full_rows, rag, backend_mode, models = load_resources()

if "bot_state" not in st.session_state:
    st.session_state.bot_state = init_state()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("Controls")
    st.caption(f"Backend: {backend_mode}")

    show_sources = st.toggle("Show sources", value=True)
    debug = st.toggle("Debug (show pipeline)", value=True)
    use_llm = st.toggle("LLM rewrite", value=True)
    rewrite_csv = st.toggle("Rewrite CSV answers", value=True)

    if st.button("Reset conversation"):
        st.session_state.bot_state = init_state()
        st.session_state.messages = []
        st.rerun()

st.markdown("## Assistant (Same logic as console)")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Type your question...")
if user_input:
    res = chat_turn(user_input, st.session_state.bot_state, full_rows, rag, debug=debug)
    out = render_answer(user_input, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug)

    if not show_sources:
        out = strip_sources(out)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": out})
    st.rerun()