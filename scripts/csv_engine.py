from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent        # …/scripts/
_PROJECT_ROOT = _SCRIPTS_DIR.parent                   # …/Chat-04-Feb 2/


def _find_csv(filename: str, override: Optional[str] = None) -> Path:
    """
    Search everywhere and return first match, or raise clear FileNotFoundError.
    """
    # 1. Explicit override always wins
    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return p

    # 2. Common fixed locations (fast)
    fixed = [
        _SCRIPTS_DIR / filename,
        _PROJECT_ROOT / filename,
        _PROJECT_ROOT / "data" / filename,
        _PROJECT_ROOT / "data_new" / filename,
        _PROJECT_ROOT / "data_vehicle" / filename,
        _PROJECT_ROOT / "data_preowned" / filename,
        _PROJECT_ROOT / "data_preowned" / "csv_preowned" / filename,
        _PROJECT_ROOT / "csv" / filename,
        _PROJECT_ROOT / "assets" / filename,
        _PROJECT_ROOT.parent / filename,
        _PROJECT_ROOT.parent / "data" / filename,
    ]
    for p in fixed:
        if p.exists():
            return p

    # 3. Recursive glob — finds the file no matter which subfolder it is in
    for p in _PROJECT_ROOT.rglob(filename):
        return p

    # 4. One level up (covers sibling project structures)
    for p in _PROJECT_ROOT.parent.rglob(filename):
        return p

    raise FileNotFoundError(
        f"\n\n[csv_engine] Cannot find '{filename}'.\n"
        f"Searched recursively under:\n"
        f"  {_PROJECT_ROOT}\n"
        f"  {_PROJECT_ROOT.parent}\n\n"
        f"Quick fix — copy '{filename}' to:\n"
        f"  {_PROJECT_ROOT / filename}\n"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _low(s: Any) -> str:
    return (str(s) or "").strip().lower()


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def format_price_usd(value: Any) -> str:
    if value in (None, "", "N/A"):
        return "N/A"
    try:
        v = float(str(value).replace(",", "").replace("$", "").strip())
        return f"${int(v):,}" if v == int(v) else f"${v:,.2f}"
    except Exception:
        return str(value).strip() or "N/A"


# ---------------------------------------------------------------------------
# Load rows
# ---------------------------------------------------------------------------

def load_full_rows(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load and return all rows from vehicle_master.csv.

    Args:
        csv_path: Optional explicit path to the CSV. Searches common project
                  locations automatically if not given.

    Returns:
        List of row dicts (one per vehicle variant).

    Raises:
        FileNotFoundError: with helpful message listing all searched locations.
    """
    path = _find_csv("vehicle_master.csv", override=csv_path)
    print(f"[csv_engine] vehicle CSV: {path}")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [dict(r) for r in csv.DictReader(f)]
    return rows


# ---------------------------------------------------------------------------
# Model detection
# ---------------------------------------------------------------------------

_MODEL_ALIASES: Dict[str, str] = {
    # ── Corolla Cross ──────────────────────────────────────────────────────
    "corolla cross gasoline": "COROLLA CROSS GASOLINE",
    "corolla cross hev": "Corolla Cross HEV",
    "corolla cross hybrid": "Corolla Cross HEV",
    "corolla cross": "COROLLA CROSS GASOLINE",

    # ── Fortuner ──────────────────────────────────────────────────────────
    "fortuner legender": "Fortuner Legender",
    "fortuner": "Fortuner Legender",

    # ── Hiace ─────────────────────────────────────────────────────────────
    "hiace 12-seater": "Hiace 12-seater",
    "hiace 12 seater": "Hiace 12-seater",
    "hiace 12": "Hiace 12-seater",
    "hiace 16-seater": "Hiace 16-seater",
    "hiace 16 seater": "Hiace 16-seater",
    "hiace 16": "Hiace 16-seater",

    # ── Hilux ─────────────────────────────────────────────────────────────
    "hilux revo rally": "Hilux Revo Rally",
    "hilux rally": "Hilux Revo Rally",
    "hilux revo v-edition": "Hilux Revo V-Edition",
    "hilux revo v edition": "Hilux Revo V-Edition",
    "hilux v-edition": "Hilux Revo V-Edition",
    "hilux revo v": "Hilux Revo V-Edition",
    "hilux": "Hilux Revo Rally",

    # 1. FIX: Add Rocco + Hilux Revo aliases (for compare like "hilux revo vs revo rocco")
    # Note: Ensure your CSV model column contains exactly "Hilux Revo Rocco"; if not, change canonical here.
    "revo rocco": "Hilux Revo Rocco",
    "hilux revo rocco": "Hilux Revo Rocco",
    "hilux rocco": "Hilux Revo Rocco",
    "hilux revo": "Hilux Revo Rally",

    # ── Land Cruiser ──────────────────────────────────────────────────────
    "land cruiser 250 diesel": "Land Cruiser 250 Diesel",
    "land cruiser 250 gasoline": "Land Cruiser 250 Gasoline",
    "land cruiser 250": "Land Cruiser 250 Diesel",
    "land cruiser gr-s": "LAND CRUISER GR-S",
    "land cruiser gr s": "LAND CRUISER GR-S",
    "land cruiser grs": "LAND CRUISER GR-S",
    "land cruiser gr": "LAND CRUISER GR-S",
    "land cruiser zx": "Land Cruiser ZX",
    "land cruiser": "Land Cruiser ZX",

    # ── Others ────────────────────────────────────────────────────────────
    "raize": "Raize",
    "veloz": "Veloz",
    "vios": "Vios",
    "wigo": "Wigo",
    "yaris cross hev": "Yaris Cross HEV",
    "yaris cross hybrid": "Yaris Cross HEV",
    "yaris cross gasoline": "YARIS CROSS GASOLINE",
    "yaris cross": "Yaris Cross HEV",
}


def _canonical_model_names(full_rows: List[Dict[str, Any]]) -> List[str]:
    seen: set = set()
    names: List[str] = []
    for r in full_rows:
        m = (r.get("model") or "").strip()
        if m and m not in seen:
            seen.add(m)
            names.append(m)
    return names


def detect_model_in_text(text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
    """
    Return CSV model name found in text (longest alias wins), or None.
    """
    t = _norm_ws(_low(text))

    # 1. Alias table — sorted longest-first so specific beats general
    for alias in sorted(_MODEL_ALIASES, key=len, reverse=True):
        if alias in t:
            canonical = _MODEL_ALIASES[alias]
            for r in full_rows:
                if _low(r.get("model", "")) == _low(canonical):
                    return r["model"]
            return canonical

    # 2. Direct match against CSV names
    names = _canonical_model_names(full_rows)
    for name in sorted(names, key=len, reverse=True):
        if _low(name) in t:
            return name

    return None


def detect_models_in_text(
    text: str,
    full_rows: List[Dict[str, Any]],
    max_models: int = 2,
) -> List[str]:
    """
    Return up to max_models distinct model names found in text.

    2. FIX: Includes alias detection (so "revo rocco" gets detected as a model).
    """
    t = _norm_ws(_low(text))
    found: List[str] = []
    used: List[Tuple[int, int]] = []

    def _add_model(model_name: str, start: int, end: int) -> None:
        if model_name and model_name not in found:
            found.append(model_name)
            used.append((start, end))

    # 2.1 Alias detection first (longest-first)
    for alias in sorted(_MODEL_ALIASES, key=len, reverse=True):
        idx = t.find(alias)
        if idx == -1:
            continue
        end = idx + len(alias)

        if any(s <= idx < e or s < end <= e for s, e in used):
            continue

        canonical = _MODEL_ALIASES[alias]
        resolved = None
        for r in full_rows:
            if _low(r.get("model", "")) == _low(canonical):
                resolved = r.get("model")
                break

        _add_model(resolved or canonical, idx, end)

        if len(found) >= max_models:
            return found[:max_models]

    # 2.2 Canonical model names next
    for name in sorted(_canonical_model_names(full_rows), key=len, reverse=True):
        pattern = _low(name)
        idx = t.find(pattern)
        if idx == -1:
            continue
        end = idx + len(pattern)

        if any(s <= idx < e or s < end <= e for s, e in used):
            continue

        _add_model(name, idx, end)

        if len(found) >= max_models:
            break

    return found[:max_models]


def resolve_target_model(
    user_text: str,
    last_model: Optional[str],
    full_rows: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Model from text first; then fall back to last_model for follow-ups.
    """
    m = detect_model_in_text(user_text, full_rows)
    return m if m else last_model


def find_row_by_model(
    full_rows: List[Dict[str, Any]],
    model_name: str,
) -> Optional[Dict[str, Any]]:
    m = _low(model_name)
    for r in full_rows:
        if _low(r.get("model", "")) == m:
            return r
    return None


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

def is_spec_intent(text: str) -> bool:
    return any(k in _low(text) for k in ["spec", "specification"])


def is_summary_intent(text: str) -> bool:
    t = _low(text)
    return "summary" in t or "overview" in t or "tell me about" in t


def is_recommendation_intent(text: str) -> bool:
    t = _low(text)
    return any(k in t for k in [
        "recommend",
        "suggest",
        "i want to buy",
        "buy a car",
        "buy car",
        "looking for a car",
        "looking to buy",
        "help me choose",
        "which car",
        "best car for",
        "best toyota",   # FIX T048/T055: "best toyota suv under 35000"
        "top toyota",
        "cheapest toyota",
        "affordable toyota",
    ])


# ---------------------------------------------------------------------------
# Slot extraction
# ---------------------------------------------------------------------------

def extract_budget(text: str) -> Optional[float]:
    t = _low(text).replace(",", "")
    m = re.search(
        r"(?:under|below|less\s+than|budget|max|<)\s*\$?\s*(\d{4,6}(?:\.\d+)?)",
        t
    )
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass

    m2 = re.search(r"\b(\d{4,6})\b", t)
    if m2:
        try:
            return float(m2.group(1))
        except Exception:
            pass
    return None


def extract_seats(text: str) -> Optional[int]:
    t = _low(text)
    m = re.search(r"(?:min|minimum|at\s+least|>)\s*(\d+)\s*seat", t)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d+)\s*seat", t)
    if m2:
        return int(m2.group(1))
    return None


def extract_fuel(text: str) -> Optional[str]:
    t = _low(text)
    if "both" in t.split():
        return "both"
    if "gasoline" in t or re.search(r"\bgas\b", t):
        return "gasoline"
    if "diesel" in t:
        return "diesel"
    if "hybrid" in t or "hev" in t:
        return "hybrid"
    if re.search(r"\bev\b", t) or "electric" in t:
        return "ev"
    return None


def extract_body_type(text: str) -> Optional[str]:
    t = _low(text)
    if "suv" in t:
        return "SUV"
    if "sedan" in t:
        return "Sedan"
    if "pickup" in t or "pick-up" in t or "pick up" in t:
        return "Pickup"
    if "mpv" in t or "mvp" in t:
        return "MPV"
    if re.search(r"\bbus\b", t):
        return "BUS"
    return None


# ---------------------------------------------------------------------------
# Feature key detection
# ---------------------------------------------------------------------------

_FEATURE_MAP: List[Tuple[str, List[str]]] = [
    # Transmission — must come before generic "engine" to win longest-match
    ("spec_transmission", ["transmission type", "transmission", "gearbox", "gear box", "gear type"]),
    ("spec_fuel_tank_capacity", ["fuel tank capacity", "fuel tank", "tank capacity"]),
    ("spec_srs_airbags", ["srs airbag", "airbag", "airbags", "number of airbags"]),
    ("seats", ["seating capacity", "seat number", "how many seats", "number of seats", "seats", "seat"]),
    ("spec_ground_clearance", ["ground clearance", "clearance"]),
    # CarPlay / Android Auto — order: longer alias first wins
    ("spec_apple_carplay_and_android_auto", [
        "apple carplay and android auto", "apple carplay or android auto",
        "apple carplay / android auto", "carplay and android auto",
        "apple carplay", "android auto", "carplay",
    ]),
    ("spec_apple_carplay_or_android_auto", [
        "apple carplay and android auto", "apple carplay or android auto",
        "apple carplay / android auto", "carplay and android auto",
        "apple carplay", "android auto", "carplay",
    ]),
    # 360 / panoramic
    ("spec_panoramic_view_monitor_pvm", [
        "360° panoramic view monitor", "panoramic view monitor", "360 camera",
        "360camera", "around view", "pvm", "360°", "360",
    ]),
    ("spec_blind_spot_monitor_bsm", ["blind spot monitor", "blind spot monitoring", "blind spot", "bsm"]),
    ("spec_headup_display_hud", ["head-up display", "heads-up display", "head up display", "hud"]),
    # Sunroof — FIX T029
    ("spec_sunroof", ["panoramic sunroof", "sunroof", "moonroof", "panoramic roof", "glass roof"]),
    ("spec_wireless_charger", ["wireless charging pad", "wireless charger", "wireless charg", "qi charging"]),
    ("spec_wireless_charging", ["wireless charging pad", "wireless charger", "wireless charg", "qi charging"]),
    ("spec_reverse_camera", ["reverse camera", "reversing camera", "backup camera", "rear camera"]),
    ("spec_parking_sensors", ["parking sensor", "parking assist"]),
    ("spec_safety_rating", ["safety rating", "ncap rating", "ncap"]),
    ("spec_lane_departure_warning_ldw", ["lane departure warning", "lane keep", "lane warning", "ldw"]),
    ("spec_vehicle_stability_control_vsc", ["vehicle stability control", "stability control", "vsc"]),
    ("spec_smart_entry", ["smart entry", "keyless entry", "smart key", "keyless"]),
    ("spec_ignition", ["push start ignition", "push start button", "ignition", "push start"]),
    ("spec_drive_type", ["drive type", "drivetrain", "4wd", "awd", "fwd", "2wd", "4x4"]),
    ("spec_displacement", ["engine displacement", "engine capacity", "displacement", "engine size", "engine cc"]),
    ("spec_engine_type", ["engine type", "engine specification", "engine"]),
    ("spec_wheelbase", ["wheelbase", "wheel base"]),
    ("spec_length___width___height", ["length width height", "dimensions", "dimension", "l x w x h", "l×w×h"]),
    ("spec_max_output", ["maximum output", "max output", "power output", "horsepower", "bhp", "hp"]),
    ("spec_max_torque", ["maximum torque", "max torque", "torque"]),
    ("fuel", ["fuel type", "type of fuel", "fuel"]),
    # Cruise control — FIX T024 / Fortuner cruise control
    ("spec_cruise_control", ["adaptive cruise control", "dynamic radar cruise", "cruise control", "drcc", "cruise"]),
]


def detect_feature_key(text: str) -> Optional[str]:
    t = _low(text)
    best_col: Optional[str] = None
    best_len = 0
    for col, keywords in _FEATURE_MAP:
        for kw in keywords:
            if kw in t and len(kw) > best_len:
                best_col = col
                best_len = len(kw)
    return best_col


# ---------------------------------------------------------------------------
# Answer builders
# ---------------------------------------------------------------------------

def answer_specs_from_csv(full_rows: List[Dict[str, Any]], model_name: str) -> Dict[str, Any]:
    row = find_row_by_model(full_rows, model_name)
    if not row:
        txt = f"I couldn't find '{model_name}' in the dataset."
        return {"answer_type": "csv_specs", "text": txt, "facts": [txt], "sources": []}

    name = row.get("model") or model_name
    price = format_price_usd(row.get("price_usd"))
    seats = row.get("seats") or "N/A"
    fuel = row.get("fuel") or "N/A"
    body = row.get("body_type") or "N/A"
    trans = row.get("spec_transmission") or row.get("spec_transmission_type") or "N/A"
    engine = row.get("spec_engine_type") or "N/A"
    src = row.get("url") or ""

    txt = (
        f"Great question! Here's a quick spec overview for the **{name}**:\n\n"
        f"**Price:** {price}\n"
        f"**Seats:** {seats}\n"
        f"**Fuel:** {fuel.title() if fuel != 'N/A' else fuel}\n"
        f"**Body type:** {body}\n"
        f"**Transmission:** {trans}\n"
        f"**Engine:** {engine}"
    )
    return {"answer_type": "csv_specs", "text": txt, "facts": [txt], "sources": [src] if src else []}


def answer_summary_from_csv(full_rows: List[Dict[str, Any]], model_name: str) -> Dict[str, Any]:
    row = find_row_by_model(full_rows, model_name)
    if not row:
        txt = f"I couldn't find '{model_name}' in the dataset."
        return {"answer_type": "csv_summary", "text": txt, "facts": [txt], "sources": []}

    name = row.get("model") or model_name
    price = format_price_usd(row.get("price_usd"))
    seats = row.get("seats") or "N/A"
    fuel = row.get("fuel") or "N/A"
    body = row.get("body_type") or "N/A"
    trans = row.get("spec_transmission") or row.get("spec_transmission_type") or "N/A"
    src = row.get("url") or ""

    txt = (
        f"Sure! Here's a quick overview of the **{name}**:\n\n"
        f"The {name} is a {fuel.title() if fuel != 'N/A' else fuel}-powered {body} "
        f"priced at **{price}**. It seats up to **{seats} passengers** and comes with "
        f"a **{trans}** transmission."
    )
    return {"answer_type": "csv_summary", "text": txt, "facts": [txt], "sources": [src] if src else []}


def answer_price_from_csv(full_rows: List[Dict[str, Any]], model_name: str) -> Dict[str, Any]:
    row = find_row_by_model(full_rows, model_name)
    if not row:
        txt = f"I couldn't find '{model_name}' in the dataset."
        return {"answer_type": "csv_price", "text": txt, "facts": [txt], "sources": []}

    name = row.get("model") or model_name
    price = format_price_usd(row.get("price_usd"))
    src = row.get("url") or ""

    txt = f"The **{name}** is priced at **{price}** (USD). Would you like to know more about its specs or features?"
    return {"answer_type": "csv_price", "text": txt, "facts": [txt], "sources": [src] if src else []}


def answer_feature_from_csv(
    full_rows: List[Dict[str, Any]],
    model_name: str,
    feature_key: str,
) -> Optional[Dict[str, Any]]:
    """
    Return feature answer or None if value is missing.
    """
    row = find_row_by_model(full_rows, model_name)
    if not row:
        return None

    name = row.get("model") or model_name
    src = row.get("url") or ""

    if feature_key == "seats":
        val = row.get("seats") or row.get("spec_seating_capacity") or ""
    elif feature_key == "fuel":
        val = row.get("fuel") or ""
    # FIX T016: spec_transmission may be empty — fall back to spec_transmission_type
    elif feature_key == "spec_transmission":
        val = row.get("spec_transmission") or row.get("spec_transmission_type") or ""
        if val:
            feature_key = "spec_transmission" if row.get("spec_transmission") else "spec_transmission_type"
    # FIX T021: try both carplay columns — one may be empty
    elif feature_key in ("spec_apple_carplay_and_android_auto", "spec_apple_carplay_or_android_auto"):
        val = (row.get("spec_apple_carplay_and_android_auto") or
               row.get("spec_apple_carplay_or_android_auto") or "")
        feature_key = "spec_apple_carplay_and_android_auto"
    else:
        # Sunroof column variations support
        if feature_key == "spec_sunroof":
            candidates = [
                "spec_sunroof",
                "spec_moonroof",
                "spec_panoramic_sunroof",
                "spec_roof",
            ]
            val = ""
            for k in candidates:
                if row.get(k):
                    val = row.get(k)
                    feature_key = k
                    break
            # Last resort: any column containing 'sunroof' or 'moonroof'
            if not val:
                for k in row.keys():
                    if ("sunroof" in _low(k) or "moonroof" in _low(k)) and row.get(k):
                        val = row.get(k)
                        feature_key = k
                        break

        # 4. FIX: Cruise control column variations support
        elif feature_key == "spec_cruise_control":
            candidates = [
                "spec_cruise_control",
                "spec_adaptive_cruise_control",
                "spec_dynamic_radar_cruise_control_drrc",
                "spec_radar_cruise_control",
            ]
            val = ""
            for k in candidates:
                if row.get(k):
                    val = row.get(k)
                    feature_key = k
                    break

            # Last resort: any column containing 'cruise'
            if not val:
                for k in row.keys():
                    if "cruise" in _low(k) and row.get(k):
                        val = row.get(k)
                        feature_key = k
                        break
        else:
            val = row.get(feature_key) or ""

    val_str = str(val).strip()
    if not val_str:
        return None

    _LABELS: Dict[str, str] = {
        "spec_transmission": "Transmission",
        "spec_transmission_type": "Transmission type",
        "spec_fuel_tank_capacity": "Fuel tank capacity",
        "spec_srs_airbags": "SRS airbags",
        "seats": "Seats",
        "spec_ground_clearance": "Ground clearance",
        "spec_apple_carplay_and_android_auto": "Apple CarPlay / Android Auto",
        "spec_apple_carplay_or_android_auto": "Apple CarPlay / Android Auto",
        "spec_panoramic_view_monitor_pvm": "360° Panoramic View Monitor",
        "spec_blind_spot_monitor_bsm": "Blind Spot Monitor",
        "spec_headup_display_hud": "Head-Up Display",
        "spec_sunroof": "Sunroof / Moonroof",
        "spec_wireless_charger": "Wireless charger",
        "spec_wireless_charging": "Wireless charging",
        "spec_reverse_camera": "Reverse camera",
        "spec_parking_sensors": "Parking sensors",
        "spec_safety_rating": "Safety rating",
        "spec_lane_departure_warning_ldw": "Lane Departure Warning",
        "spec_vehicle_stability_control_vsc": "Vehicle Stability Control",
        "spec_smart_entry": "Smart entry",
        "spec_ignition": "Ignition",
        "spec_drive_type": "Drive type",
        "spec_displacement": "Displacement",
        "spec_engine_type": "Engine type",
        "spec_wheelbase": "Wheelbase",
        "spec_length___width___height": "Dimensions (L×W×H)",
        "spec_max_output": "Max output",
        "spec_max_torque": "Max torque",
        "fuel": "Fuel type",

        # 5. FIX: Cruise control labels
        "spec_cruise_control": "Cruise control",
        "spec_adaptive_cruise_control": "Adaptive cruise control",
        "spec_dynamic_radar_cruise_control_drrc": "Dynamic Radar Cruise Control",
        "spec_radar_cruise_control": "Radar cruise control",
    }
    label = _LABELS.get(feature_key, feature_key.replace("spec_", "").replace("_", " ").title())

    _YES = {"included", "yes", "available", "standard"}
    _NO = {"not available", "n/a", "no", "not included"}

    vl = val_str.lower()
    if vl in _YES:
        verdict = "Yes"
    elif vl in _NO:
        verdict = "No"
    else:
        verdict = val_str

    if verdict.lower() == "yes":
        txt = f"Yes. The **{name}** includes **{label}**."
    elif verdict.lower() == "no":
        txt = f"No. The **{name}** does not include **{label}**."
    else:
        txt = f"The **{name}** has **{label}**: **{verdict}**."

    return {"answer_type": "csv_feature", "text": txt, "facts": [txt], "sources": [src] if src else []}


# ---------------------------------------------------------------------------
# Recommendation filtering
# ---------------------------------------------------------------------------

def filter_cars_split(
    full_rows: List[Dict[str, Any]],
    max_budget: float,
    min_seats: int,
    fuel: Optional[str],
    body_type: Optional[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Return (verified_matches, possible_matches_seats_short).
    """
    verified: List[Dict[str, Any]] = []
    possible: List[Dict[str, Any]] = []

    for r in full_rows:
        try:
            price = float(str(r.get("price_usd", "0")).replace(",", "").replace("$", ""))
        except Exception:
            continue
        if price > max_budget:
            continue

        rfuel = _low(r.get("fuel") or "")
        rbody = _low(r.get("body_type") or "")
        fuel_ok = fuel is None or fuel == "both" or fuel in rfuel
        body_ok = body_type is None or _low(body_type) == rbody

        try:
            rseats = int(str(r.get("seats") or "0").strip())
        except Exception:
            rseats = 0

        seats_ok = min_seats == 0 or rseats >= min_seats

        if fuel_ok and body_ok:
            (verified if seats_ok else possible).append(r)

    return verified, possible


def build_reco_answer(
    verified: List[Dict[str, Any]],
    possible: List[Dict[str, Any]],
    max_items: int = 5,
    assumed_seats: Optional[int] = None,
) -> Dict[str, Any]:
    if not verified and not possible:
        txt = (
            "I couldn't find a perfect match with those filters. "
            "Try a slightly higher budget or a different body type / fuel."
        )
        return {"answer_type": "csv_reco", "text": txt, "facts": [txt], "sources": []}

    show = verified or possible
    note = "" if verified else "\n(These may not fully meet your seat requirement.)"
    lines = ["Here are some Toyota models that match your preferences:\n"]
    sources: List[str] = []

    for i, r in enumerate(show[:max_items], 1):
        name = r.get("model") or "N/A"
        price = format_price_usd(r.get("price_usd"))
        seats = r.get("seats") or "N/A"
        rfuel = (r.get("fuel") or "N/A").title()
        rbody = r.get("body_type") or "N/A"
        lines.append(f"{i}. {name}")
        lines.append(f"   {price} | {seats} seats | {rfuel} | {rbody}")
        u = r.get("url") or ""
        if u and u not in sources:
            sources.append(u)

    lines.append("\nReply with a listing number (1–10) or model name to see more details.")
    if note:
        lines.append(note)

    txt = "\n".join(lines)
    return {"answer_type": "csv_reco", "text": txt, "facts": [txt], "sources": sources}