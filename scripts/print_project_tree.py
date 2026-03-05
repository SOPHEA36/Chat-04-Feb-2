# import json
# import os
# from collections import Counter, defaultdict
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Any, Dict, List, Optional, Tuple
#
# import pandas as pd
#
#
# @dataclass
# class JsonProfile:
#     path: str
#     root_type: str
#     top_keys: List[str]
#     sample: Dict[str, Any]
#     error: str = ""
#
#
# def safe_read_text(p: Path, max_bytes: int = 500_000) -> str:
#     data = p.read_bytes()
#     if len(data) > max_bytes:
#         data = data[:max_bytes]
#     return data.decode("utf-8", errors="replace")
#
#
# def scan_tree(root: Path, max_depth: int = 4) -> List[Path]:
#     root = root.resolve()
#     out: List[Path] = []
#
#     def depth(p: Path) -> int:
#         try:
#             return len(p.relative_to(root).parts)
#         except Exception:
#             return 999
#
#     for p in root.rglob("*"):
#         if depth(p) <= max_depth:
#             out.append(p)
#     return out
#
#
# def print_tree(root: Path, max_depth: int = 4) -> None:
#     root = root.resolve()
#     print(f"\nFOLDER TREE (max_depth={max_depth})")
#     print(str(root))
#
#     def walk(cur: Path, prefix: str = "", level: int = 0) -> None:
#         if level > max_depth:
#             return
#         try:
#             entries = sorted(list(cur.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
#         except Exception:
#             return
#
#         for i, e in enumerate(entries):
#             is_last = i == len(entries) - 1
#             connector = "└── " if is_last else "├── "
#             print(prefix + connector + e.name)
#             if e.is_dir():
#                 extension = "    " if is_last else "│   "
#                 walk(e, prefix + extension, level + 1)
#
#     walk(root, "", 0)
#
#
# def profile_json_file(p: Path) -> JsonProfile:
#     try:
#         txt = safe_read_text(p)
#         obj = json.loads(txt)
#
#         if isinstance(obj, dict):
#             keys = list(obj.keys())
#             sample = {}
#             for k in keys[:12]:
#                 v = obj.get(k)
#                 if isinstance(v, (dict, list)):
#                     sample[k] = f"<{type(v).__name__}>"
#                 else:
#                     sample[k] = v
#             return JsonProfile(str(p), "dict", keys[:50], sample)
#
#         if isinstance(obj, list):
#             if len(obj) == 0:
#                 return JsonProfile(str(p), "list(empty)", [], {})
#             first = obj[0]
#             if isinstance(first, dict):
#                 keys = list(first.keys())
#                 sample = {}
#                 for k in keys[:12]:
#                     v = first.get(k)
#                     if isinstance(v, (dict, list)):
#                         sample[k] = f"<{type(v).__name__}>"
#                     else:
#                         sample[k] = v
#                 return JsonProfile(str(p), "list(dict)", keys[:50], sample)
#             return JsonProfile(str(p), f"list({type(first).__name__})", [], {"first_item": str(first)[:160]})
#
#         return JsonProfile(str(p), type(obj).__name__, [], {"value": str(obj)[:160]})
#     except Exception as e:
#         return JsonProfile(str(p), "unknown", [], {}, error=str(e))
#
#
# def summarize_json_folder(folder: Path, max_files: int = 40) -> None:
#     files = sorted(folder.rglob("*.json"))
#     print(f"\nJSON SUMMARY: {folder}")
#     print(f"JSON files: {len(files)}")
#
#     profiles = [profile_json_file(p) for p in files[:max_files]]
#
#     type_counts = Counter([pr.root_type for pr in profiles])
#     print("Root types:", dict(type_counts))
#
#     key_counter = Counter()
#     for pr in profiles:
#         key_counter.update(pr.top_keys)
#
#     if key_counter:
#         common = key_counter.most_common(40)
#         print("\nMost common keys (top 40):")
#         for k, c in common:
#             print(f"  {k}: {c}")
#
#     errors = [pr for pr in profiles if pr.error]
#     if errors:
#         print("\nJSON parse errors (first 5):")
#         for pr in errors[:5]:
#             print(f"  {pr.path} -> {pr.error}")
#
#     print("\nExample JSON file samples (first 3):")
#     for pr in profiles[:3]:
#         print(f"- {pr.path}")
#         print(f"  root_type: {pr.root_type}")
#         if pr.error:
#             print(f"  error: {pr.error}")
#         else:
#             print(f"  sample: {pr.sample}")
#
#
# def summarize_csv_folder(folder: Path, max_files: int = 10) -> None:
#     files = sorted(folder.rglob("*.csv"))
#     print(f"\nCSV SUMMARY: {folder}")
#     print(f"CSV files: {len(files)}")
#
#     for p in files[:max_files]:
#         try:
#             df = pd.read_csv(p)
#             print(f"\n- {p.name}  rows={len(df)} cols={len(df.columns)}")
#             print("  columns:", list(df.columns)[:60])
#             na = df.isna().sum().sort_values(ascending=False).head(10)
#             print("  top missing (col: count):", {k: int(v) for k, v in na.items() if int(v) > 0})
#         except Exception as e:
#             print(f"\n- {p.name}  ERROR reading CSV: {e}")
#
#
# def file_type_counts(root: Path) -> None:
#     exts = Counter()
#     for p in root.rglob("*"):
#         if p.is_file():
#             exts[p.suffix.lower()] += 1
#     top = exts.most_common(20)
#     print("\nFILE TYPE COUNTS (top 20):")
#     for ext, c in top:
#         print(f"  {ext or '<no_ext>'}: {c}")
#
#
# def summarize_quick_copy_paste(root: Path, json_dir: Optional[Path], csv_dir: Optional[Path], docs_dir: Optional[Path], chroma_dir: Optional[Path]) -> None:
#     print("\n" + "=" * 70)
#     print("COPY/PASTE SUMMARY (send this to me)")
#     print("=" * 70)
#     print(f"ROOT: {root}")
#     if json_dir:
#         print(f"JSON_DIR: {json_dir} (json files: {len(list(json_dir.rglob('*.json')))} )")
#     if csv_dir:
#         print(f"CSV_DIR: {csv_dir} (csv files: {len(list(csv_dir.rglob('*.csv')))} )")
#     if docs_dir:
#         print(f"DOCS_DIR: {docs_dir} (txt files: {len(list(docs_dir.rglob('*.txt')))} )")
#     if chroma_dir:
#         exists = chroma_dir.exists()
#         print(f"CHROMA_DIR: {chroma_dir} (exists: {exists})")
#     print("=" * 70 + "\n")
#
#
# def main():
#     # Update this root to your folder
#     root = Path(r"/").resolve()
#
#     json_dir = root / "data_preowned" / "json_preowned"
#     docs_dir = root / "data_preowned" / "docs_preowned"
#     csv_dir = root / "data_preowned" / "csv_preowned"
#     chroma_dir = root / "vector_db" / "chroma_preowned"
#
#     print("Scanning root:", root)
#     if not root.exists():
#         raise FileNotFoundError(f"Root not found: {root}")
#
#     file_type_counts(root)
#
#     if json_dir.exists():
#         summarize_json_folder(json_dir, max_files=40)
#     else:
#         print(f"\nJSON_DIR not found: {json_dir}")
#
#     if csv_dir.exists():
#         summarize_csv_folder(csv_dir, max_files=10)
#     else:
#         print(f"\nCSV_DIR not found: {csv_dir}")
#
#     summarize_quick_copy_paste(root, json_dir, csv_dir, docs_dir, chroma_dir)
#
#
# if __name__ == "__main__":
#     main()

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".idea",
    ".vscode",
    "outputs",
}

EXCLUDE_EXT = {
    ".pyc",
    ".log",
    ".sqlite",
    ".db",
}


def print_tree(path: Path, prefix: str = ""):
    items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))

    for i, item in enumerate(items):
        if item.name in EXCLUDE_DIRS:
            continue
        if item.suffix in EXCLUDE_EXT:
            continue

        connector = "└── " if i == len(items) - 1 else "├── "
        print(prefix + connector + item.name)

        if item.is_dir():
            new_prefix = prefix + ("    " if i == len(items) - 1 else "│   ")
            print_tree(item, new_prefix)


if __name__ == "__main__":
    print(f"\nProject Root: {PROJECT_ROOT}\n")
    print_tree(PROJECT_ROOT)