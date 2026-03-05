# chat_slots.py
import csv
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_MIN = PROJECT_ROOT / "data" / "csv" / "vehicle_master_min.csv"
CSV_FULL = PROJECT_ROOT / "data" / "csv" / "vehicle_master.csv"

FUELS = {"diesel", "gasoline", "hybrid", "ev", "any"}
BODY_TYPES = {"suv", "sedan", "pickup", "bus", "mpv", "mvp", "any"}

FEATURE_MAP = {
    "camera_360": {
        "aliases": [
            "360 camera", "camera 360", "360-degree camera", "around view", "panoramic view",
            "bird view", "birds eye", "surround view", "pvm", "panoramic view monitor"
        ],
        "columns": ["spec_panoramic_view_monitor_pvm"],
        "label": "360° camera (Panoramic View Monitor)"
    },
    "reverse_camera": {
        "aliases": ["reverse camera", "rear camera", "backup camera", "reversing camera"],
        "columns": ["spec_reverse_camera"],
        "label": "reverse camera"
    },
    "adaptive_cruise": {
        "aliases": ["adaptive cruise", "acc", "drcc", "radar cruise", "dynamic radar cruise"],
        "columns": [
            "spec_fullspeed_range_adaptive_cruise_control_acc",
            "spec_dynamic_radar_cruise_control_drcc",
            "spec_cruise_control",
        ],
        "label": "adaptive cruise control"
    },
    "bsm": {
        "aliases": ["blind spot", "bsm", "blind spot monitor"],
        "columns": ["spec_blind_spot_monitor_bsm"],
        "label": "blind spot monitor (BSM)"
    },
    "carplay_android": {
        "aliases": ["carplay", "apple carplay", "android auto", "car play"],
        "columns": [
            "spec_apple_carplay_and_android_auto",
            "spec_apple_carplay_or_android_auto",
        ],
        "label": "Apple CarPlay / Android Auto"
    },
    "airbags": {
        "aliases": ["airbag", "airbags", "srs airbags", "srs airbag"],
        "columns": ["spec_srs_airbags"],
        "label": "SRS airbags"
    },
    "parking_sensors": {
        "aliases": ["parking sensor", "parking sensors", "sensor parking"],
        "columns": ["spec_parking_sensors"],
        "label": "parking sensors"
    },
    "wireless_charging": {
        "aliases": ["wireless charger", "wireless charging", "qi charging"],
        "columns": ["spec_wireless_charger", "spec_wireless_charging"],
        "label": "wireless charging"
    },
    "ahb": {
        "aliases": ["automatic high beam", "ahb", "auto high beam"],
        "columns": ["spec_automatic_high_beam_ahb"],
        "label": "Automatic High Beam (AHB)"
    },
    "ldw": {
        "aliases": ["lane departure warning", "ldw"],
        "columns": ["spec_lane_departure_warning_ldw"],
        "label": "Lane Departure Warning (LDW)"
    },
    "lkc": {
        "aliases": ["lane keeping", "lane keep", "lkc", "lka"],
        "columns": ["spec_lane_keeping_control_lkc"],
        "label": "Lane Keeping Control (LKC)"
    },
    "pcw_pcb": {
        "aliases": ["pre-collision", "pre collision", "pcw", "pcb", "aeb", "automatic emergency braking"],
        "columns": ["spec_precollision_warning_pcw", "spec_precollision_braking_pcb"],
        "label": "Pre-Collision Warning/Braking"
    },
    "abs": {
        "aliases": ["abs", "antilock braking", "anti lock braking"],
        "columns": ["spec_antilock_braking_system_abs"],
        "label": "ABS"
    },
    "vsc": {
        "aliases": ["vsc", "stability control", "vehicle stability control"],
        "columns": ["spec_vehicle_stability_control_vsc"],
        "label": "Vehicle Stability Control (VSC)"
    },
}


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return int(float(s))
    except Exception:
        return None


def extract_budget(text: str) -> Optional[int]:
    m = re.search(r"\$?\s*([\d,]{4,})", text)
    if not m:
        return None
    n = m.group(1).replace(",", "")
    if n.isdigit():
        return int(n)
    return None


def extract_seats(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:seat|seats|seater)\b", text, flags=re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


def extract_fuel(text: str) -> Optional[str]:
    t = text.lower()
    for f in FUELS:
        if re.search(rf"\b{f}\b", t):
            return f
    return None


def extract_body_type(text: str) -> Optional[str]:
    t = text.lower()
    for b in BODY_TYPES:
        if re.search(rf"\b{b}\b", t):
            if b == "mvp":
                return "mpv"
            return b
    return None


def is_recommendation_question(text: str) -> bool:
    t = text.lower()
    if extract_budget(t) is not None:
        return True
    if extract_seats(t) is not None:
        return True
    if extract_fuel(t) is not None:
        return True
    if extract_body_type(t) is not None:
        return True
    if any(k in t for k in ["recommend", "suggest", "buy", "budget", "looking for", "need a car"]):
        return True
    return False


def detect_feature_key(text: str) -> Optional[str]:
    t = text.lower()

    if "camera" in t and "360" in t:
        return "camera_360"

    for key, meta in FEATURE_MAP.items():
        for a in meta["aliases"]:
            if a in t:
                return key
    return None


def normalize_model_name(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def detect_model_in_text(text: str, full_rows: List[Dict[str, Any]]) -> Optional[str]:
    t = normalize_model_name(text)
    candidates = []
    for r in full_rows:
        m = normalize_model_name(str(r.get("model", "")))
        if m and m in t:
            candidates.append(m)
    if not candidates:
        return None
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def resolve_target_model(user_text: str, last_model: Optional[str], full_rows: List[Dict[str, Any]]) -> Optional[str]:
    mentioned = detect_model_in_text(user_text, full_rows)
    if mentioned:
        return mentioned

    t = user_text.lower()
    if any(p in t for p in ["it", "this model", "that model", "this one", "the car"]):
        return last_model

    return last_model


def yn_from_value(val: Any) -> Optional[bool]:
    if val is None:
        return None
    s = str(val).strip().lower()
    if not s:
        return None
    if s in ["yes", "true", "1", "available", "standard", "included"]:
        return True
    if s in ["no", "false", "0", "not available", "na", "n/a", "none"]:
        return False
    return None


def find_row_by_model(full_rows: List[Dict[str, Any]], model_norm: str) -> Optional[Dict[str, Any]]:
    for r in full_rows:
        m = normalize_model_name(str(r.get("model", "")))
        if m == model_norm:
            return r
    return None


def answer_feature_from_csv(full_rows: List[Dict[str, Any]], model_norm: str, feature_key: str) -> Optional[str]:
    row = find_row_by_model(full_rows, model_norm)
    if not row:
        return None

    meta = FEATURE_MAP[feature_key]
    for col in meta["columns"]:
        if col in row and row.get(col) not in [None, ""]:
            val = row.get(col)
            yn = yn_from_value(val)

            model_name = row.get("model") or "This model"
            src = row.get("url") or ""

            if yn is True:
                ans = f"Yes — {model_name} has {meta['label']}."
            elif yn is False:
                ans = f"No — {model_name} does not list {meta['label']} in the official specs."
            else:
                ans = f"{model_name}: {meta['label']} = {val}"

            if src:
                ans += f" Source: {src}"
            return ans

    return None


def filter_cars(rows: List[Dict[str, Any]], max_budget: int, min_seats: int, fuel: str, body_type: str) -> List[Dict[str, Any]]:
    fuel = fuel.lower().strip()
    body_type = body_type.lower().strip()
    out = []

    for r in rows:
        price = to_int(r.get("price_usd"))
        seats = to_int(r.get("seats"))
        row_fuel = (r.get("fuel") or "").lower().strip()
        row_body = (r.get("body_type") or "").lower().strip()

        if price is None or seats is None:
            continue
        if price > max_budget:
            continue
        if seats < min_seats:
            continue
        if fuel != "any" and row_fuel != fuel:
            continue
        if body_type != "any" and row_body != body_type:
            continue

        out.append(r)

    out.sort(key=lambda x: to_int(x.get("price_usd")) or 10**12)
    return out


def ask_missing(slots: Dict[str, Any]) -> Optional[str]:
    missing = []
    if slots.get("max_budget") is None:
        missing.append("What is your maximum budget (USD)? (example: 50000)")
    if slots.get("min_seats") is None:
        missing.append("How many seats do you strictly need? (example: 5 seats, 7 seats, 12 seats)")
    if slots.get("fuel") is None:
        missing.append("Fuel preference: Diesel / Gasoline / Hybrid / EV / Any")
    if slots.get("body_type") is None:
        missing.append("Body type: SUV / Sedan / MPV / Pickup / Bus / Any")
    if not missing:
        return None
    return "To give you a precise recommendation from our official data, please tell me:\n- " + "\n- ".join(missing)


def main():
    min_rows = load_csv(CSV_MIN)
    full_rows = load_csv(CSV_FULL)

    slots = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
    last_model: Optional[str] = None

    print("Car Chatbot (Recommendation + CSV Feature Q&A)")
    print("Type 'exit' to quit. Type 'new' to restart.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break
        if user.lower() == "new":
            slots = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
            last_model = None
            print("\nBot: Restarted. Tell me your budget, seats, fuel, body type, or ask a feature question.\n")
            continue

        mentioned_model = detect_model_in_text(user, full_rows)
        if mentioned_model:
            last_model = mentioned_model

        feature_key = detect_feature_key(user)
        if feature_key:
            target_model = resolve_target_model(user, last_model, full_rows)
            if not target_model:
                print("\nBot: Which model should I check? (example: Yaris Cross, Corolla Cross)\n")
                continue

            last_model = target_model
            ans = answer_feature_from_csv(full_rows, target_model, feature_key)
            if ans:
                print(f"\nBot: {ans}\n")
            else:
                print("\nBot: I couldn't find this feature in the structured specs fields. Ask another feature or specify a different model.\n")
            continue

        if is_recommendation_question(user):
            b = extract_budget(user)
            s = extract_seats(user)
            f = extract_fuel(user)
            bt = extract_body_type(user)

            if b is not None and slots["max_budget"] is None:
                slots["max_budget"] = b
            if s is not None and slots["min_seats"] is None:
                slots["min_seats"] = s
            if f is not None and slots["fuel"] is None:
                slots["fuel"] = f
            if bt is not None and slots["body_type"] is None:
                slots["body_type"] = bt

            followup = ask_missing(slots)
            if followup:
                print(f"\nBot: {followup}\n")
                continue

            matches = filter_cars(min_rows, slots["max_budget"], slots["min_seats"], slots["fuel"], slots["body_type"])
            if not matches:
                print("\nBot: I couldn't find an official match with those constraints.")
                print("Bot: Try increasing budget, lowering seats, changing body type, or choosing 'Any' fuel.\n")
                continue

            print("\nBot: Based on your requirements, here are official matches:\n")
            for m in matches:
                print(f"- {m['brand']} {m['model']} (${m['price_usd']}), seats={m['seats']}, fuel={m['fuel']}, body={m['body_type']}")
                print(f"  Source: {m['url']}\n")

            slots = {"max_budget": None, "min_seats": None, "fuel": None, "body_type": None}
            print("Bot: If you want another recommendation, tell me your budget, seats, fuel, and body type.\n")
            continue

        print("\nBot: I can help with:\n- Recommendations (budget, seats, fuel, body type)\n- Feature questions (e.g., 'Does Yaris Cross have 360 camera?')\n")


if __name__ == "__main__":
    main()