import json
import os
import re
import urllib.error
import urllib.request
from typing import List, Optional


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def ollama_generate(prompt: str, model: str) -> Optional[str]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "top_p": 0.9},
    }

    url = "http://localhost:11434/api/generate"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode("utf-8"))
            text = (out.get("response") or "").strip()
            return text if text else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


_GREETING_RE = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|thx)\b", re.IGNORECASE)


def _is_small_talk(text: str) -> bool:
    if not text:
        return False
    t = text.strip().lower()
    if _GREETING_RE.match(t):
        return True
    if t in {"ok", "okay", "nice", "great", "cool"}:
        return True
    return False


def llm_rewrite(user_q: str, factual_text: str, facts: List[str], sources: List[str]) -> str:
    if _is_small_talk(user_q):
        return "Hi! Tell me what you want to know (price, specs, features, compare, or recommendation)."

    if not facts:
        return (factual_text or "").strip() or "I couldn't produce an answer."

    prompt = f"""
You are a Toyota Cambodia assistant.

Rewrite the answer to sound natural and helpful.
Hard rules:
- Use ONLY the information in FACTS and FACTUAL_ANSWER.
- Do NOT add or guess anything.
- 1 to 3 sentences only.
- Output ONLY the rewritten answer text. No labels, no JSON, no extra lines.

USER_QUESTION:
{user_q}

FACTUAL_ANSWER:
{factual_text}

FACTS:
{json.dumps(facts, ensure_ascii=False)}
""".strip()

    model = get_ollama_model()
    out = ollama_generate(prompt, model)
    if not out:
        return (factual_text or "").strip() or "I couldn't produce an answer."

    out = out.strip()

    # Safety cleanup: if the model leaks instructions, fallback
    bad_markers = ["FACTUAL_ANSWER", "FACTSJSON", "SOURCES_JSON", "ANSWER:", "SOURCES:"]
    if any(m.lower() in out.lower() for m in bad_markers):
        return (factual_text or "").strip() or "I couldn't produce an answer."

    # Keep it short
    out = re.sub(r"\s+", " ", out).strip()
    return out