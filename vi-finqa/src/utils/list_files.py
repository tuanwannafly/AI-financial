from __future__ import annotations

from pathlib import Path
from typing import List


def list_txt_files(raw_dir: str = "data/raw") -> List[Path]:
    return sorted(Path(raw_dir).rglob("*.txt"))


def count_by_extension(raw_dir: str = "data/raw") -> dict:
    root = Path(raw_dir)
    counts: dict[str, int] = {}
    for p in root.rglob("*"):
        if p.is_file():
            ext = p.suffix.lower() or "<noext>"
            counts[ext] = counts.get(ext, 0) + 1
    return counts


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", default="data/raw")
    args = parser.parse_args()
    files = list_txt_files(args.raw_dir)
    print(json.dumps({"n_txt": len(files), "ext_counts": count_by_extension(args.raw_dir)}, ensure_ascii=False, indent=2))
