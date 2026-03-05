import json
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "data_preowned" / "docs_preowned"
OUT_DIR = PROJECT_ROOT / "data_preowned" / "processed_preowned"
OUT_JSONL = OUT_DIR / "preowned_chunks.jsonl"


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(DOCS_DIR.rglob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No txt docs found in: {DOCS_DIR}")

    n = 0
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for fp in txt_files:
            content = fp.read_text(encoding="utf-8", errors="replace")
            pieces = chunk_text(content)

            for i, ch in enumerate(pieces):
                rec: Dict[str, object] = {
                    "id": f"{fp.stem}__chunk{i:03d}",
                    "source_file": str(fp),
                    "chunk_index": i,
                    "text": ch,
                    "doc_type": "preowned",
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1

    print(f"Docs: {len(txt_files)}")
    print(f"Chunks: {n}")
    print(f"Saved: {OUT_JSONL}")


if __name__ == "__main__":
    main()