import json
from pathlib import Path


def validate_day4(
    metadata_path: str = "data/extracted/metadata.jsonl",
    review_path: str = "data/processed/review_queue.jsonl",
    normalized_path: str = "data/processed/normalized_terms.jsonl",
    ontology_path: str = "src/schema/ontology.yaml",
    long_path: str = "data/processed/long_format.jsonl",
) -> dict:
    result = {
        "ontology_exists": Path(ontology_path).exists(),
        "metadata_exists": Path(metadata_path).exists(),
        "normalized_exists": Path(normalized_path).exists(),
        "review_exists": Path(review_path).exists(),
        "long_exists": Path(long_path).exists(),
        "n_metadata": 0,
        "n_normalized": 0,
        "n_mapped": 0,
        "n_review": 0,
        "n_long_rows": 0,
        "pass": False,
    }

    meta = Path(metadata_path)
    if meta.exists():
        with meta.open(encoding="utf-8") as f:
            result["n_metadata"] = sum(1 for line in f if line.strip())

    norm = Path(normalized_path)
    if norm.exists():
        with norm.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                result["n_normalized"] += 1
                r = json.loads(line)
                if r.get("canonical"):
                    result["n_mapped"] += 1

    rev = Path(review_path)
    if rev.exists():
        with rev.open(encoding="utf-8") as f:
            result["n_review"] = sum(1 for line in f if line.strip())

    longp = Path(long_path)
    if longp.exists():
        with longp.open(encoding="utf-8") as f:
            result["n_long_rows"] = sum(1 for line in f if line.strip())

    # Day 4 AC: ontology + metadata processed into normalized + review queue + long format
    result["pass"] = (
        result["ontology_exists"]
        and result["metadata_exists"]
        and result["normalized_exists"]
        and result["review_exists"]
        and result["long_exists"]
        and (result["n_metadata"] == 0 or result["n_normalized"] > 0)
        and result["n_long_rows"] > 0
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", default="data/extracted/metadata.jsonl")
    parser.add_argument("--review", default="data/processed/review_queue.jsonl")
    parser.add_argument("--normalized", default="data/processed/normalized_terms.jsonl")
    parser.add_argument("--ontology", default="src/schema/ontology.yaml")
    parser.add_argument("--long", default="data/processed/long_format.jsonl")
    args = parser.parse_args()
    print(
        json.dumps(
            validate_day4(args.metadata, args.review, args.normalized, args.ontology, args.long),
            ensure_ascii=False,
            indent=2,
        )
    )
