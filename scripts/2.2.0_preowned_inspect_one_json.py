import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = PROJECT_ROOT / "data_preowned" / "json_preowned"


def main():
    files = sorted(JSON_DIR.rglob("*.json"))
    if not files:
        raise FileNotFoundError(f"No json found in: {JSON_DIR}")

    fp = files[0]
    obj = json.loads(fp.read_text(encoding="utf-8", errors="replace"))

    print("FILE:", fp)
    print("TYPE:", type(obj).__name__)

    if isinstance(obj, list):
        print("LIST LEN:", len(obj))
        if obj and isinstance(obj[0], dict):
            obj = obj[0]

    if isinstance(obj, dict):
        print("TOP KEYS:")
        for k in list(obj.keys())[:80]:
            v = obj.get(k)
            t = type(v).__name__
            preview = str(v)[:120].replace("\n", " ")
            print(f"- {k} ({t}): {preview}")
    else:
        print(str(obj)[:500])


if __name__ == "__main__":
    main()