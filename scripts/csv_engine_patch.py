from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

def detect_models_in_text(text: str, full_rows: List[Dict[str, Any]], max_models: int = 2) -> List[str]:
    t = (text or "").lower()
    found: List[str] = []
    for r in full_rows:
        name = str(r.get("model") or "").strip()
        if not name:
            continue
        if name.lower() in t and name not in found:
            found.append(name)
        if len(found) >= max_models:
            break
    return found

def detect_model_in_text(text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
    xs = detect_models_in_text(text, full_rows, max_models=1)
    return xs[0] if xs else None