import streamlit as st
import time
from scripts.chat_assistant import (
    load_full_rows,
    build_rag_engine,
    chat_turn,
    render_answer,
    _reset_state
)

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Toyota RAG Assistant",
    page_icon="🚗",
    layout="centered"
)

# --- 2. DARK THEME & BRANDING (CSS) ---
st.markdown("""
    <style>
    /* Main Background - Dark Charcoal */
    .stApp { 
        background-color: #0E1117; 
        color: #FFFFFF;
    }

    /* Chat Bubbles */
    .stChatMessage { 
        border-radius: 15px; 
        background-color: #262730; /* Slightly lighter gray for bubbles */
        border: 1px solid #333;
    }

    /* Input Bar styling */
    .stChatInputContainer {
        padding-bottom: 20px;
        background-color: transparent;
    }

    /* Toyota Red for the Send button */
    button[kind="primary"] { 
        background-color: #eb0a1e; 
        border: none; 
        color: white;
    }

    /* Fix text visibility in dark mode */
    h1, h2, h3, p, span {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)


# --- 3. INITIALIZE DATA & ENGINE ---
@st.cache_resource
def load_resources():
    rows = load_full_rows()
    rag = build_rag_engine(rows)
    return rows, rag


full_rows, rag = load_resources()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "logic_state" not in st.session_state:
    st.session_state.logic_state = {}
    _reset_state(st.session_state.logic_state)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("Toyota Menu")
    if st.button("🗑️ Reset Chat"):
        st.session_state.messages = []
        _reset_state(st.session_state.logic_state)
        st.rerun()
    st.divider()
    debug_mode = st.toggle("Show Logic Tags", value=False)

# --- 5. CHAT GUI ---
st.title("🚗 Toyota Intelligence")
st.markdown("##### *Dark Edition*")

for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🏎️"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about Toyota models..."):
    st.chat_message("user", avatar="👤").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar="🏎️"):
        response_placeholder = st.empty()

        # Process Logic
        res = chat_turn(prompt, st.session_state.logic_state, full_rows, rag, debug=debug_mode)
        full_answer = render_answer(prompt, res, use_llm=True, rewrite_csv=False, debug=debug_mode)

        # Typewriter effect
        displayed_text = ""
        for word in full_answer.split(" "):
            displayed_text += word + " "
            response_placeholder.markdown(displayed_text + "▌")
            time.sleep(0.02)
        response_placeholder.markdown(full_answer)

    st.session_state.messages.append({"role": "assistant", "content": full_answer})