from __future__ import annotations

import json
from pathlib import Path
from typing import List

import jsonlines

from .normalize import normalize_batch
from .longify import run_longify


def collect_raw_terms(metadata_path: str = "data/extracted/metadata.jsonl") -> List[str]:
    terms: List[str] = []
    path = Path(metadata_path)
    if not path.exists():
        return terms
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            for row in rec.get("rows") or []:
                if row and isinstance(row[0], str) and row[0].strip():
                    terms.append(row[0].strip())
    return terms


def run_normalize(
    metadata_path: str = "data/extracted/metadata.jsonl",
    out_path: str = "data/processed/normalized_terms.jsonl",
    review_path: str = "data/processed/review_queue.jsonl",
    ontology_path: str = "src/schema/ontology.yaml",
    long_path: str = "data/processed/long_format.jsonl",
) -> dict:
    terms = collect_raw_terms(metadata_path)
    seen = set()
    unique: List[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    results, review_queue = normalize_batch(unique, ontology_path=ontology_path)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(out_path, mode="w") as w:
        for r in results:
            w.write(r)
    with jsonlines.open(review_path, mode="w") as w:
        for r in review_queue:
            w.write(r)

    long_stats = run_longify(metadata_path, long_path)

    return {
        "n_terms": len(unique),
        "n_mapped": sum(1 for r in results if r["canonical"] is not None),
        "n_review": len(review_queue),
        "out_path": out_path,
        "review_path": review_path,
        "long_format": long_stats,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", default="data/extracted/metadata.jsonl")
    parser.add_argument("--out", default="data/processed/normalized_terms.jsonl")
    parser.add_argument("--review", default="data/processed/review_queue.jsonl")
    parser.add_argument("--ontology", default="src/schema/ontology.yaml")
    parser.add_argument("--long", default="data/processed/long_format.jsonl")
    args = parser.parse_args()
    stats = run_normalize(args.metadata, args.out, args.review, args.ontology, args.long)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
