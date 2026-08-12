from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .sample_explore import sample_files, scan_file, TABLE_HEADER_HINTS


OCR_ISSUE_HINTS = [
    ("số dính chữ", r"[A-Za-zÀ-ỹ]\d|\d[A-Za-zÀ-ỹ]"),
    ("dấu phẩy/chấm lẫn", r"\d+,\d{3}\.\d|\d+\.\d{3},\d"),
    ("số âm (123)", r"\(\s*[\d.,]+\s*\)"),
    ("ký tự lạ OCR", r"[|¦�]"),
    ("space lạ giữa số", r"\d\s+\d"),
]


def detect_ocr_issues(text: str) -> List[str]:
    import re

    found = []
    for name, pat in OCR_ISSUE_HINTS:
        if re.search(pat, text):
            found.append(name)
    return found or ["(chưa quan sát rõ trong mẫu này)"]


def detect_table_types(hits: dict) -> List[str]:
    types = []
    mapping = [
        ("CĐKT", TABLE_HEADER_HINTS[0]),
        ("KQKD", TABLE_HEADER_HINTS[1]),
        ("LCTT", TABLE_HEADER_HINTS[2]),
        ("Thuyết minh", TABLE_HEADER_HINTS[3]),
    ]
    for label, key in mapping:
        if hits.get(key):
            types.append(label)
    return types or ["UNKNOWN"]


def write_exploration_notes(
    raw_dir: str = "data/raw",
    out_path: str = "notes/data_exploration.md",
    n: int = 25,
    seed: int = 42,
) -> dict:
    files = sample_files(raw_dir, n=n, seed=seed)
    blocks = []
    ocr_kinds = set()
    for f in files:
        info = scan_file(f)
        text = f.read_text(encoding="utf-8", errors="ignore")
        ocr = detect_ocr_issues(text)
        for x in ocr:
            if not x.startswith("("):
                ocr_kinds.add(x)
        types = detect_table_types(info["hits"])
        hits_str = {k: len(v) for k, v in info["hits"].items() if v}
        blocks.append(
            f"""## File: {info['path']}
- Số dòng: {info['n_lines']}
- Table markers tìm thấy: {hits_str}
- OCR issues quan sát: {', '.join(ocr)}
- Table types xuất hiện: {', '.join(types)}
"""
        )

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(blocks), encoding="utf-8")
    return {
        "n_files_scanned": len(files),
        "n_blocks": len(blocks),
        "ocr_kinds": sorted(ocr_kinds),
        "out_path": out_path,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", default="data/raw")
    parser.add_argument("--out", default="notes/data_exploration.md")
    parser.add_argument("--n", type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(write_exploration_notes(args.raw_dir, args.out, args.n), ensure_ascii=False, indent=2))
