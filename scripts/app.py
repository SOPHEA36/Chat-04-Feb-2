#
# import sys
# from pathlib import Path
#
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))
#
# import time
# from datetime import datetime
# import streamlit as st
#
# from scripts.csv_engine import load_full_rows
# from scripts.chat_assistant import build_rag_engine, chat_turn, render_answer, _reset_state
#
# st.set_page_config(page_title="Toyota Intelligence", page_icon="🚗", layout="centered")
#
# THEME_CSS = """
# <style>
# :root{
#   --bg-start: #081426;
#   --bg-end:   #162a46;
#
#   --glass: rgba(15, 23, 42, 0.55);
#   --glass2: rgba(30, 41, 59, 0.45);
#
#   --line: rgba(255,255,255,0.12);
#   --text: #e2e8f0;
#   --muted: rgba(226,232,240,0.70);
#
#   --accent: #3b82f6;
#   --accent2:#22c55e;
#   --danger:#ff4d5a;
#
#   --user1: rgba(59,130,246,0.95);
#   --user2: rgba(37,99,235,0.78);
#
#   --bot1: rgba(30, 41, 59, 0.86);
#   --bot2: rgba(51, 65, 85, 0.74);
#
#   --bubble-max: 520px;
#   --bubble-max-md: 420px;
#   --bubble-max-sm: 320px;
# }
#
# .stApp{
#   background:
#     radial-gradient(1000px 650px at 18% -10%, rgba(59,130,246,0.28) 0%, transparent 60%),
#     radial-gradient(900px 650px at 96% 12%, rgba(34,197,94,0.18) 0%, transparent 62%),
#     radial-gradient(900px 650px at 92% 82%, rgba(255,77,90,0.10) 0%, transparent 60%),
#     linear-gradient(135deg, var(--bg-start), var(--bg-end));
#   color: var(--text);
#   font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
# }
#
# header[data-testid="stHeader"]{ background: transparent !important; }
# footer{ visibility:hidden; }
# .block-container{ padding-top: 1.0rem !important; padding-bottom: 1.6rem !important; }
#
# [data-testid="stChatMessageAvatar"]{ display:none !important; }
# [data-testid="stChatMessage"]{ background: transparent !important; border:none !important; padding:0 !important; }
# .stChatMessage{ margin-bottom: 10px !important; }
#
# .header-card{
#   border: 1px solid var(--line);
#   background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
#   border-radius: 18px;
#   padding: 14px 16px;
#   margin-bottom: 12px;
#   box-shadow: 0 18px 45px rgba(0,0,0,0.28);
#   backdrop-filter: blur(10px);
# }
# .header-top{
#   display:flex;
#   align-items:center;
#   justify-content:space-between;
#   gap: 12px;
# }
# .header-title{
#   font-size: 18px;
#   font-weight: 850;
#   margin: 0;
#   letter-spacing: 0.2px;
# }
# .header-sub{
#   font-size: 13px;
#   opacity: 0.85;
#   margin-top: 6px;
#   margin-bottom: 0;
# }
# .agent-badge{
#   display:inline-flex;
#   align-items:center;
#   gap: 8px;
#   border: 1px solid rgba(255,255,255,0.14);
#   background: rgba(15,23,42,0.35);
#   padding: 8px 10px;
#   border-radius: 999px;
#   font-size: 12px;
#   font-weight: 750;
#   color: rgba(226,232,240,0.90);
# }
# .agent-dot{
#   width: 9px;
#   height: 9px;
#   border-radius: 50%;
#   background: rgba(34,197,94,0.95);
#   box-shadow: 0 0 0 3px rgba(34,197,94,0.18);
# }
#
# .chat-row{
#   display:flex;
#   flex-direction: column;
#   width: 100%;
#   margin: 8px 0;
# }
# .chat-row.user{ align-items: flex-end; }
# .chat-row.bot{ align-items: flex-start; }
#
# .bubble{
#   display:inline-block;
#   max-width: var(--bubble-max);
#   width: fit-content;
#   padding: 12px 16px;
#   border-radius: 16px;
#   border: 1px solid rgba(255,255,255,0.12);
#   line-height: 1.55;
#   font-size: 15px;
#   white-space: normal;
#   overflow-wrap: break-word;
#   word-wrap: break-word;
#   box-shadow: 0 10px 26px rgba(0,0,0,0.22);
# }
#
# .bubble.user{
#   background: linear-gradient(135deg, var(--user1), var(--user2));
#   border-color: rgba(255,255,255,0.14);
#   color: #FFFFFF;
#   border-bottom-right-radius: 8px;
#   text-align: left;
# }
# .bubble.bot{
#   background: linear-gradient(180deg, var(--bot1), var(--bot2));
#   border-color: rgba(255,255,255,0.10);
#   color: var(--text);
#   border-bottom-left-radius: 8px;
# }
#
# .msg-time{
#   margin-top: 6px;
#   font-size: 11px;
#   color: rgba(255,255,255,0.58);
# }
# .chat-row.user .msg-time{ text-align:right; padding-right: 8px; }
# .chat-row.bot .msg-time{ text-align:left;  padding-left:  8px; }
#
# a{ color: var(--danger) !important; text-decoration:none; font-weight:750; }
# a:hover{ text-decoration:underline; }
#
# details{
#   border: 1px solid rgba(255,255,255,0.10) !important;
#   border-radius: 14px !important;
#   background: rgba(255,255,255,0.03) !important;
#   padding: 8px 12px !important;
#   margin-top: 8px !important;
# }
# details summary{
#   font-size: 13px !important;
#   font-weight: 800 !important;
#   color: rgba(255,255,255,0.86) !important;
#   cursor: pointer;
# }
#
# .meta-pill{
#   display:inline-block;
#   padding: 3px 10px;
#   border-radius: 999px;
#   border: 1px solid rgba(255,255,255,0.12);
#   background: rgba(255,255,255,0.05);
#   color: rgba(255,255,255,0.78);
#   font-size: 12px;
#   font-weight: 800;
#   margin-top: 8px;
# }
#
# .stMarkdown p{ margin:0; }
#
# section[data-testid="stSidebar"]{
#   background: rgba(8,10,14,0.75) !important;
#   border-right: 1px solid rgba(255,255,255,0.08) !important;
# }
# .stButton button{
#   border-radius: 12px !important;
#   border: 1px solid rgba(255,255,255,0.12) !important;
#   background: rgba(255,255,255,0.06) !important;
#   color: rgba(255,255,255,0.92) !important;
# }
# .stButton button:hover{
#   border-color: rgba(59,130,246,0.55) !important;
#   background: rgba(59,130,246,0.14) !important;
# }
#
# ::-webkit-scrollbar { width: 8px; height: 8px; }
# ::-webkit-scrollbar-track { background: rgba(30,41,59,0.30); border-radius: 4px; }
# ::-webkit-scrollbar-thumb { background: rgba(59,130,246,0.50); border-radius: 4px; }
# ::-webkit-scrollbar-thumb:hover { background: rgba(59,130,246,0.72); }
#
# [data-testid="stChatInput"],
# [data-testid="stChatInput"] *{
#   background: transparent !important;
#   box-shadow: none !important;
# }
#
# [data-testid="stChatInput"]{
#   padding-top: 14px !important;
#   padding-bottom: 6px !important;
# }
#
# [data-testid="stChatInput"] > div{
#   background: rgba(255,255,255,0.06) !important;
#   border: 1px solid rgba(255,255,255,0.25) !important;
#   border-radius: 999px !important;
#   padding: 10px 16px !important;
#   backdrop-filter: blur(14px);
#   box-shadow: 0 18px 45px rgba(0,0,0,0.35);
#   transition: all 0.2s ease;
# }
#
# [data-testid="stChatInput"] textarea{
#   background: transparent !important;
#   border: none !important;
#   border-radius: 999px !important;
#   color: rgba(255,255,255,0.95) !important;
#   padding: 8px 6px !important;
#   min-height: 42px !important;
#   height: 42px !important;
#   line-height: 1.2 !important;
#   resize: none !important;
#   overflow-y: hidden !important;
# }
#
# [data-testid="stChatInput"] textarea::placeholder{
#   color: rgba(255,255,255,0.5) !important;
# }
#
# [data-testid="stChatInput"] > div:focus-within{
#   border-color: rgba(59,130,246,0.8) !important;
#   box-shadow:
#     0 0 0 3px rgba(59,130,246,0.20),
#     0 18px 45px rgba(0,0,0,0.35) !important;
# }
#
# [data-testid="stChatInput"] button{
#   border-radius: 999px !important;
#   border: 1px solid rgba(255,255,255,0.25) !important;
#   background: rgba(59,130,246,0.25) !important;
#   transition: all 0.2s ease;
# }
# [data-testid="stChatInput"] button:hover{
#   background: rgba(59,130,246,0.45) !important;
#   border-color: rgba(59,130,246,0.8) !important;
# }
#
# .typing-dots{
#   display: inline-flex;
#   gap: 5px;
#   padding: 2px 0;
#   align-items: center;
# }
# .typing-dots span{
#   width: 7px;
#   height: 7px;
#   border-radius: 50%;
#   background: rgba(226,232,240,0.60);
#   animation: bounce 1.25s infinite ease-in-out both;
# }
# .typing-dots span:nth-child(1){ animation-delay: -0.32s; }
# .typing-dots span:nth-child(2){ animation-delay: -0.16s; }
#
# @keyframes bounce{
#   0%, 80%, 100%{ transform: scale(0); opacity: 0.55; }
#   40%{ transform: scale(1); opacity: 1; }
# }
#
# @media (max-width: 768px){
#   .bubble{ max-width: var(--bubble-max-md); font-size: 14px; padding: 10px 12px; }
# }
# @media (max-width: 480px){
#   .bubble{ max-width: var(--bubble-max-sm); }
# }
# </style>
# """
# st.markdown(THEME_CSS, unsafe_allow_html=True)
#
# @st.cache_resource
# def load_resources():
#     rows = load_full_rows()
#     rag = build_rag_engine(rows)
#     return rows, rag
#
# def split_sources_and_pipeline(answer: str):
#     text = answer or ""
#     sources = []
#     pipeline = None
#
#     if "[PIPELINE=" in text:
#         parts = text.rsplit("[PIPELINE=", 1)
#         text = parts[0].rstrip()
#         pipeline = parts[1].replace("]", "").strip()
#
#     if "\nSources:" in text:
#         main, src = text.split("\nSources:", 1)
#         text = main.strip()
#         sources = [s.strip() for s in src.split(",") if s.strip()]
#
#     return text, sources, pipeline
#
# def _escape_html(text: str) -> str:
#     return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
#
# def _fmt_time(ts: float | None) -> str:
#     if not ts:
#         return ""
#     return datetime.fromtimestamp(ts).strftime("%I:%M %p").lstrip("0").lower()
#
# def render_bubble(role: str, text: str, ts: float | None = None):
#     role_class = "user" if role == "user" else "bot"
#     bubble_class = role_class
#     safe_text = _escape_html(text)
#     time_txt = _fmt_time(ts)
#     time_html = f'<div class="msg-time">{_escape_html(time_txt)}</div>' if time_txt else ""
#
#     st.markdown(
#         f"""
#         <div class="chat-row {role_class}">
#             <div>
#               <div class="bubble {bubble_class}">{safe_text}</div>
#               {time_html}
#             </div>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )
#
# def typing_bubble(full_text: str, speed: float = 0.0016):
#     placeholder = st.empty()
#
#     placeholder.markdown(
#         """
#         <div class="chat-row bot">
#           <div class="bubble bot">
#             <span class="typing-dots"><span></span><span></span><span></span></span>
#           </div>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )
#     time.sleep(0.5)
#
#     rendered = ""
#     for ch in full_text:
#         rendered += ch
#         safe_text = _escape_html(rendered)
#         placeholder.markdown(
#             f"""
#             <div class="chat-row bot">
#               <div class="bubble bot">{safe_text}<span style="opacity:.7">▌</span></div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )
#         time.sleep(speed)
#
#     safe_text = _escape_html(full_text)
#     placeholder.markdown(
#         f"""
#         <div class="chat-row bot">
#           <div class="bubble bot">{safe_text}</div>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )
#
# def render_meta(sources: list[str], pipeline: str | None, show_pipeline: bool):
#     if sources:
#         with st.expander("Sources"):
#             for u in sources:
#                 st.markdown(u)
#
#     if show_pipeline and pipeline:
#         st.markdown(f'<div class="meta-pill">PIPELINE: {pipeline}</div>', unsafe_allow_html=True)
#
# full_rows, rag = load_resources()
#
# if "messages" not in st.session_state:
#     st.session_state.messages = []
#
# if "logic_state" not in st.session_state:
#     st.session_state.logic_state = {}
#     _reset_state(st.session_state.logic_state)
#
# with st.sidebar:
#     st.title("Settings")
#     debug_mode = st.toggle("Show pipeline tag", value=False)
#     use_llm = st.toggle("LLM rewrite (RAG)", value=True)
#     rewrite_csv = st.toggle("Rewrite CSV answers", value=False)
#
#     st.divider()
#
#     if st.button("Reset chat", use_container_width=True):
#         st.session_state.messages = []
#         _reset_state(st.session_state.logic_state)
#         st.rerun()
#
#     if st.button("Hard reload data", use_container_width=True):
#         st.cache_resource.clear()
#         st.rerun()
#
# st.markdown(
#     """
#     <div class="header-card">
#       <div class="header-top">
#         <div>
#           <p class="header-title">Toyota Intelligence</p>
#           <p class="header-sub">Car recommendation & specs assistant (based on your dataset).</p>
#         </div>
#         <div class="agent-badge">
#           <span class="agent-dot"></span>
#           Online Agent
#         </div>
#       </div>
#     </div>
#     """,
#     unsafe_allow_html=True,
# )
#
# for m in st.session_state.messages:
#     render_bubble(m["role"], m["text"], ts=m.get("ts"))
#     if m["role"] == "assistant":
#         render_meta(m.get("sources", []), m.get("pipeline"), show_pipeline=debug_mode)
#
# prompt = st.chat_input("Ask about price, specs, compare, or recommendation...")
# if prompt:
#     user_ts = time.time()
#
#     st.session_state.messages.append(
#         {"role": "user", "text": prompt, "sources": [], "pipeline": None, "ts": user_ts}
#     )
#     render_bubble("user", prompt, ts=user_ts)
#
#     from scripts.chat_assistant import build_preowned_engine
#
#     preowned_csv = "/Users/sophea/My Document/RUPP_MITE/My Thesis Project/Final Project/Development/04-02 Chatbot/Chat-04-Feb 2/data_preowned/csv_preowned/preowned_master.csv"
#     preowned = build_preowned_engine(preowned_csv)
#
#     res = chat_turn(prompt, st.session_state.logic_state, full_rows, rag, preowned, debug=debug_mode)
#     full_answer = render_answer(prompt, res, use_llm=use_llm, rewrite_csv=rewrite_csv, debug=debug_mode)
#     main_text, sources, pipeline = split_sources_and_pipeline(full_answer)
#
#     typing_bubble(main_text, speed=0.0016)
#     render_meta(sources, pipeline, show_pipeline=debug_mode)
#
#     st.session_state.messages.append(
#         {"role": "assistant", "text": main_text, "sources": sources, "pipeline": pipeline, "ts": time.time()}
#     )
#
#     st.rerun()

#5th-March-26

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.csv_engine import load_full_rows
from scripts.chat_assistant import build_rag_engine, chat_turn, render_answer, _reset_state, build_preowned_engine

st.set_page_config(page_title="Toyota Intelligence", layout="centered")

THEME_CSS = """
<style>
:root{
  --bg-start: #081426;
  --bg-end:   #162a46;

  --glass: rgba(15, 23, 42, 0.55);
  --glass2: rgba(30, 41, 59, 0.45);

  --line: rgba(255,255,255,0.12);
  --text: #e2e8f0;
  --muted: rgba(226,232,240,0.70);

  --accent: #3b82f6;
  --accent2:#22c55e;
  --danger:#ff4d5a;

  --user1: rgba(59,130,246,0.95);
  --user2: rgba(37,99,235,0.78);

  --bot1: rgba(30, 41, 59, 0.86);
  --bot2: rgba(51, 65, 85, 0.74);

  --bubble-max: 520px;
  --bubble-max-md: 420px;
  --bubble-max-sm: 320px;
}

.stApp{
  background:
    radial-gradient(1000px 650px at 18% -10%, rgba(59,130,246,0.28) 0%, transparent 60%),
    radial-gradient(900px 650px at 96% 12%, rgba(34,197,94,0.18) 0%, transparent 62%),
    radial-gradient(900px 650px at 92% 82%, rgba(255,77,90,0.10) 0%, transparent 60%),
    linear-gradient(135deg, var(--bg-start), var(--bg-end));
  color: var(--text);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

header[data-testid="stHeader"]{ background: transparent !important; }
footer{ visibility:hidden; }
.block-container{ padding-top: 1.0rem !important; padding-bottom: 1.6rem !important; }

[data-testid="stChatMessageAvatar"]{ display:none !important; }
[data-testid="stChatMessage"]{ background: transparent !important; border:none !important; padding:0 !important; }
.stChatMessage{ margin-bottom: 10px !important; }

.header-card{
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
  border-radius: 18px;
  padding: 14px 16px;
  margin-bottom: 12px;
  box-shadow: 0 18px 45px rgba(0,0,0,0.28);
  backdrop-filter: blur(10px);
}
.header-top{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 12px;
}
.header-title{
  font-size: 18px;
  font-weight: 850;
  margin: 0;
  letter-spacing: 0.2px;
}
.header-sub{
  font-size: 13px;
  opacity: 0.85;
  margin-top: 6px;
  margin-bottom: 0;
}
.agent-badge{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(15,23,42,0.35);
  padding: 8px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 750;
  color: rgba(226,232,240,0.90);
}
.agent-dot{
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: rgba(34,197,94,0.95);
  box-shadow: 0 0 0 3px rgba(34,197,94,0.18);
}

.chat-row{
  display:flex;
  flex-direction: column;
  width: 100%;
  margin: 8px 0;
}
.chat-row.user{ align-items: flex-end; }
.chat-row.bot{ align-items: flex-start; }

.bubble{
  display:inline-block;
  max-width: var(--bubble-max);
  width: fit-content;
  padding: 12px 16px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.12);
  line-height: 1.55;
  font-size: 15px;
  white-space: normal;
  overflow-wrap: break-word;
  word-wrap: break-word;
  box-shadow: 0 10px 26px rgba(0,0,0,0.22);
}

.bubble.user{
  background: linear-gradient(135deg, var(--user1), var(--user2));
  border-color: rgba(255,255,255,0.14);
  color: #FFFFFF;
  border-bottom-right-radius: 8px;
  text-align: left;
}
.bubble.bot{
  background: linear-gradient(180deg, var(--bot1), var(--bot2));
  border-color: rgba(255,255,255,0.10);
  color: var(--text);
  border-bottom-left-radius: 8px;
}

.msg-time{
  margin-top: 6px;
  font-size: 11px;
  color: rgba(255,255,255,0.58);
}
.chat-row.user .msg-time{ text-align:right; padding-right: 8px; }
.chat-row.bot .msg-time{ text-align:left;  padding-left:  8px; }

a{ color: var(--danger) !important; text-decoration:none; font-weight:750; }
a:hover{ text-decoration:underline; }

details{
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,0.03) !important;
  padding: 8px 12px !important;
  margin-top: 8px !important;
}
details summary{
  font-size: 13px !important;
  font-weight: 800 !important;
  color: rgba(255,255,255,0.86) !important;
  cursor: pointer;
}

.meta-pill{
  display:inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.78);
  font-size: 12px;
  font-weight: 800;
  margin-top: 8px;
}

.stMarkdown p{ margin:0; }

section[data-testid="stSidebar"]{
  background: rgba(8,10,14,0.75) !important;
  border-right: 1px solid rgba(255,255,255,0.08) !important;
}
.stButton button{
  border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  background: rgba(255,255,255,0.06) !important;
  color: rgba(255,255,255,0.92) !important;
}
.stButton button:hover{
  border-color: rgba(59,130,246,0.55) !important;
  background: rgba(59,130,246,0.14) !important;
}

[data-testid="stChatInput"],
[data-testid="stChatInput"] *{
  background: transparent !important;
  box-shadow: none !important;
}

[data-testid="stChatInput"]{
  padding-top: 14px !important;
  padding-bottom: 6px !important;
}

[data-testid="stChatInput"] > div{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.25) !important;
  border-radius: 999px !important;
  padding: 10px 16px !important;
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 45px rgba(0,0,0,0.35);
  transition: all 0.2s ease;
}

[data-testid="stChatInput"] textarea{
  background: transparent !important;
  border: none !important;
  border-radius: 999px !important;
  color: rgba(255,255,255,0.95) !important;
  padding: 8px 6px !important;
  min-height: 42px !important;
  height: 42px !important;
  line-height: 1.2 !important;
  resize: none !important;
  overflow-y: hidden !important;
}

[data-testid="stChatInput"] textarea::placeholder{
  color: rgba(255,255,255,0.5) !important;
}

[data-testid="stChatInput"] > div:focus-within{
  border-color: rgba(59,130,246,0.8) !important;
  box-shadow:
    0 0 0 3px rgba(59,130,246,0.20),
    0 18px 45px rgba(0,0,0,0.35) !important;
}

[data-testid="stChatInput"] button{
  border-radius: 999px !important;
  border: 1px solid rgba(255,255,255,0.25) !important;
  background: rgba(59,130,246,0.25) !important;
  transition: all 0.2s ease;
}
[data-testid="stChatInput"] button:hover{
  background: rgba(59,130,246,0.45) !important;
  border-color: rgba(59,130,246,0.8) !important;
}

.typing-dots{
  display: inline-flex;
  gap: 5px;
  padding: 2px 0;
  align-items: center;
}
.typing-dots span{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(226,232,240,0.60);
  animation: bounce 1.25s infinite ease-in-out both;
}
.typing-dots span:nth-child(1){ animation-delay: -0.32s; }
.typing-dots span:nth-child(2){ animation-delay: -0.16s; }

@keyframes bounce{
  0%, 80%, 100%{ transform: scale(0); opacity: 0.55; }
  40%{ transform: scale(1); opacity: 1; }
}

@media (max-width: 768px){
  .bubble{ max-width: var(--bubble-max-md); font-size: 14px; padding: 10px 12px; }
}
@media (max-width: 480px){
  .bubble{ max-width: var(--bubble-max-sm); }
}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


@st.cache_resource
def load_resources():
    rows = load_full_rows()
    rag = build_rag_engine(rows)
    return rows, rag


@st.cache_resource
def load_preowned_engine():
    default_csv = str(PROJECT_ROOT / "data_preowned" / "csv_preowned" / "preowned_master.csv")
    csv_path = os.environ.get("PREOWNED_CSV_PATH") or default_csv
    return build_preowned_engine(csv_path)


def split_sources_and_pipeline(answer: str):
    text = answer or ""
    sources = []
    pipeline = None

    if "[PIPELINE=" in text:
        parts = text.rsplit("[PIPELINE=", 1)
        text = parts[0].rstrip()
        pipeline = parts[1].replace("]", "").strip()

    if "\nSources:" in text:
        main, src = text.split("\nSources:", 1)
        text = main.strip()
        sources = [s.strip() for s in src.split(",") if s.strip()]

    return text, sources, pipeline


def _escape_html(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_time(ts: float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts).strftime("%I:%M %p").lstrip("0").lower()


def render_bubble(role: str, text: str, ts: float | None = None):
    role_class = "user" if role == "user" else "bot"
    safe_text = _escape_html(text)
    time_txt = _fmt_time(ts)
    time_html = f'<div class="msg-time">{_escape_html(time_txt)}</div>' if time_txt else ""

    st.markdown(
        f"""
        <div class="chat-row {role_class}">
            <div>
              <div class="bubble {role_class}">{safe_text}</div>
              {time_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def typing_bubble(full_text: str, enabled: bool, speed: float):
    if not enabled:
        render_bubble("assistant", full_text, ts=time.time())
        return

    placeholder = st.empty()

    placeholder.markdown(
        """
        <div class="chat-row bot">
          <div class="bubble bot">
            <span class="typing-dots"><span></span><span></span><span></span></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(0.15)

    s = full_text or ""
    n = len(s)
    if n == 0:
        return

    chunk_size = 40 if n >= 400 else 24
    for i in range(0, n, chunk_size):
        rendered = s[: i + chunk_size]
        safe_text = _escape_html(rendered)
        placeholder.markdown(
            f"""
            <div class="chat-row bot">
              <div class="bubble bot">{safe_text}<span style="opacity:.7">▌</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(speed)

    safe_text = _escape_html(s)
    placeholder.markdown(
        f"""
        <div class="chat-row bot">
          <div class="bubble bot">{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_meta(sources: list[str], pipeline: str | None, show_pipeline: bool, max_sources: int):
    if sources:
        with st.expander("Sources"):
            for u in sources[:max_sources]:
                st.markdown(u)

    if show_pipeline and pipeline:
        st.markdown(f'<div class="meta-pill">PIPELINE: {pipeline}</div>', unsafe_allow_html=True)


full_rows, rag = load_resources()
preowned = load_preowned_engine()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "logic_state" not in st.session_state:
    st.session_state.logic_state = {}
    _reset_state(st.session_state.logic_state)


with st.sidebar:
    st.title("Settings")

    fast_mode = st.toggle("Fast mode (recommended)", value=True)

    debug_mode = st.toggle("Show pipeline tag", value=False, disabled=fast_mode)
    use_llm = st.toggle("LLM rewrite (RAG)", value=True)
    rewrite_csv = st.toggle("Rewrite CSV answers", value=False)

    st.divider()

    typing_enabled = st.toggle("Typing animation", value=False if fast_mode else True)
    typing_speed = st.slider("Typing speed", 0.0, 0.03, 0.006, 0.001, disabled=fast_mode)

    max_sources = st.slider("Max sources to show", 1, 10, 5)

    st.divider()

    if st.button("Reset chat", use_container_width=True):
        st.session_state.messages = []
        _reset_state(st.session_state.logic_state)
        st.rerun()

    if st.button("Hard reload data", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()


st.markdown(
    """
    <div class="header-card">
      <div class="header-top">
        <div>
          <p class="header-title">Toyota Intelligence</p>
          <p class="header-sub">Car recommendation & specs assistant (based on your dataset).</p>
        </div>
        <div class="agent-badge">
          <span class="agent-dot"></span>
          Online Agent
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Render history once per run
for m in st.session_state.messages:
    render_bubble(m["role"], m["text"], ts=m.get("ts"))
    if m["role"] == "assistant":
        render_meta(
            m.get("sources", []),
            m.get("pipeline"),
            show_pipeline=(debug_mode and not fast_mode),
            max_sources=max_sources,
        )

prompt = st.chat_input("Ask about price, specs, compare, or recommendation...")
if prompt:
    user_ts = time.time()
    st.session_state.messages.append(
        {"role": "user", "text": prompt, "sources": [], "pipeline": None, "ts": user_ts}
    )
    render_bubble("user", prompt, ts=user_ts)

    # Do not force another rerun after processing; it slows down.
    with st.spinner("Thinking..."):
        t0 = time.perf_counter()

        res = chat_turn(prompt, st.session_state.logic_state, full_rows, rag, preowned, debug=(debug_mode and not fast_mode))
        full_answer = render_answer(
            prompt,
            res,
            use_llm=use_llm,
            rewrite_csv=rewrite_csv,
            debug=(debug_mode and not fast_mode),
        )

        main_text, sources, pipeline = split_sources_and_pipeline(full_answer)
        _ = (time.perf_counter() - t0)

    typing_bubble(main_text, enabled=(typing_enabled and not fast_mode), speed=float(typing_speed))
    render_meta(sources, pipeline, show_pipeline=(debug_mode and not fast_mode), max_sources=max_sources)

    st.session_state.messages.append(
        {"role": "assistant", "text": main_text, "sources": sources, "pipeline": pipeline, "ts": time.time()}
    )

    st.rerun()