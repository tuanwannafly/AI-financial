"""Attach ontology canonical labels to long-format rows."""
from __future__ import annotations

import json
from pathlib import Path


def load_term_map(normalized_path: str = "data/processed/normalized_terms.jsonl") -> dict[str, dict]:
    m: dict[str, dict] = {}
    p = Path(normalized_path)
    if not p.exists():
        return m
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            raw = r.get("raw")
            if raw is not None:
                m[raw] = r
    return m


def attach_canonical(
    long_path: str = "data/processed/long_format.jsonl",
    normalized_path: str = "data/processed/normalized_terms.jsonl",
    out_path: str = "data/processed/long_format_mapped.jsonl",
) -> dict:
    term_map = load_term_map(normalized_path)
    src = Path(long_path)
    if not src.exists():
        return {"pass": False, "reason": f"missing {long_path}"}

    n = 0
    n_mapped = 0
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with src.open(encoding="utf-8") as f, out.open("w", encoding="utf-8") as w:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            info = term_map.get(row.get("chỉ_tiêu", ""), {})
            row["canonical"] = info.get("canonical")
            row["confidence"] = info.get("confidence", 0.0)
            if row["canonical"]:
                n_mapped += 1
            w.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return {
        "n_long_rows": n,
        "n_mapped_rows": n_mapped,
        "map_rate": n_mapped / n if n else 0.0,
        "out_path": out_path,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--long", default="data/processed/long_format.jsonl")
    parser.add_argument("--normalized", default="data/processed/normalized_terms.jsonl")
    parser.add_argument("--out", default="data/processed/long_format_mapped.jsonl")
    args = parser.parse_args()
    print(json.dumps(attach_canonical(args.long, args.normalized, args.out), ensure_ascii=False, indent=2))
