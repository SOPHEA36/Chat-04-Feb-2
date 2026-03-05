from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# 1. Style configuration (easy to tweak without touching logic)
@dataclass(frozen=True)
class StyleConfig:
    include_sources: bool = True
    include_followups: bool = True
    max_sources: int = 3

    friendly_greeting: bool = True
    compact_lists: bool = True

    # Pre-owned formatting
    preowned_show_overview: bool = True
    preowned_max_items: int = 10


# 2. Default style used by your app/tests unless you pass another config
DEFAULT_STYLE = StyleConfig()


# 3. Small text helpers
def _low(s: Any) -> str:
    return (str(s) or "").strip().lower()


def _clean_spaces(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _normalize_sources(sources: Any, max_sources: int) -> List[str]:
    if not sources:
        return []
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list):
        return []

    out: List[str] = []
    for s in sources:
        u = (str(s) or "").strip()
        if not u:
            continue
        if u not in out:
            out.append(u)
        if len(out) >= max_sources:
            break
    return out


def _pick_followup(answer_type: str, user_text: str) -> Optional[str]:
    t = _low(user_text)

    if answer_type in {"csv_price", "csv_specs", "csv_summary"}:
        return "Do you want specs, key features, or a comparison with another model?"

    if answer_type in {"csv_feature"}:
        return "Do you want me to check another feature too (CarPlay, airbags, 360 camera)?"

    if answer_type in {"csv_compare"}:
        return "If you tell me your budget and fuel preference, I can recommend the best match."

    if answer_type in {"csv_reco"}:
        return "Which one do you want details for? You can reply with the model name."

    if answer_type in {"preowned"}:
        if "price" in t or "how much" in t or "cost" in t:
            return "If you share your budget and preferred year, I can narrow it down."
        return "Reply with a listing number (1–10) or plate number to see more details."

    return None


def _format_preowned(text: str, config: StyleConfig) -> str:
    """
    Make pre-owned output more friendly and less "robotic", without changing engine logic.
    This function assumes your preowned_engine already returns plain text.
    """
    t = _clean_spaces(text)

    # If it already looks good, keep it.
    if not t:
        return t

    # Make the headline friendlier
    t = re.sub(
        r"^I found\s+\*\*(\d+)\s+pre-owned listings\*\*:?",
        r"Here are **\1 Toyota Certified Pre-Owned** options I found:",
        t,
        flags=re.IGNORECASE,
    )

    # Fix weird broken numbers like:
    # 51
    # ,
    # 900
    t = re.sub(r"(\d)\s*\n\s*,\s*\n\s*(\d)", r"\1,\2", t)

    # Reduce repeated "Overview:" noise a bit
    if not config.preowned_show_overview:
        t = re.sub(r"^Overview:.*$", "", t, flags=re.IGNORECASE | re.MULTILINE).strip()

    return _clean_spaces(t)


# 4. Main function you will import and use everywhere
def style_answer(
    user_text: str,
    res: Dict[str, Any],
    config: StyleConfig = DEFAULT_STYLE,
) -> str:
    # 4.1 Base text
    text = str(res.get("answer") or res.get("text") or "").strip()
    if not text:
        facts = res.get("facts")
        if isinstance(facts, list) and facts:
            text = str(facts[0] or "").strip()

    if not text:
        text = "Sorry — I couldn't produce an answer."

    # 4.2 Normalize by answer type
    answer_type = str(res.get("answer_type") or "").strip()

    if answer_type == "preowned":
        text = _format_preowned(text, config)

    # 4.3 Optional follow-up line
    if config.include_followups:
        follow = _pick_followup(answer_type, user_text)
        if follow:
            # Avoid duplicating if your engine already ends with the same line
            if _low(follow) not in _low(text):
                text = _clean_spaces(text + "\n\n" + follow)

    # 4.4 Sources formatting
    sources = _normalize_sources(res.get("sources"), config.max_sources)

    # Avoid duplicate Sources block
    if config.include_sources and sources:
        if "sources:" not in _low(text):
            text = _clean_spaces(text + "\n\nSources: " + ", ".join(sources))