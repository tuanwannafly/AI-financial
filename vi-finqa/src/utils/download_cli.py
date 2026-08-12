"""CLI to download ViFinQA from HuggingFace.

Usage:
  py -m src.utils.download_cli --repo_id <ORG/NAME> [--local_dir data/raw]
"""
from __future__ import annotations

import argparse
import json

from .download import download_dataset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo_id",
        default="AIGuruTinix/ViFinQA",
        help="HuggingFace dataset repo id (default: AIGuruTinix/ViFinQA)",
    )
    parser.add_argument("--local_dir", default="data/raw")
    args = parser.parse_args()
    path = download_dataset(args.repo_id, args.local_dir)
    print(json.dumps({"ok": True, "path": path, "repo_id": args.repo_id}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
