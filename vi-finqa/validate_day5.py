import json
from collections import Counter
from pathlib import Path


REQUIRED_CATEGORIES = {
    "simple_lookup",
    "calculation",
    "multi_table",
    "company_compare",
    "thuyet_minh",
}


def validate_day5(
    gold_path: str = "data/gold/gold_set.json",
    human_batch: str = "data/gold/human_review_batch.json",
    min_n: int = 150,
) -> dict:
    gold_file = Path(gold_path)
    if not gold_file.exists():
        return {"pass": False, "reason": f"missing {gold_path}"}

    gold = json.loads(gold_file.read_text(encoding="utf-8"))
    cats = Counter(g.get("category") for g in gold)
    n_verified = sum(1 for g in gold if g.get("verified_by_execution") is True)
    batch_exists = Path(human_batch).exists()
    batch_n = 0
    if batch_exists:
        batch = json.loads(Path(human_batch).read_text(encoding="utf-8"))
        batch_n = len(batch)

    covered_cats = set(c for c in cats if c in REQUIRED_CATEGORIES)
    result = {
        "n_gold": len(gold),
        "n_verified": n_verified,
        "categories": dict(cats),
        "n_categories_covered": len(covered_cats),
        "human_review_batch_exists": batch_exists,
        "human_review_batch_n": batch_n,
        "pass": (
            len(gold) >= min_n
            and n_verified == len(gold)
            and len(covered_cats) >= 5
            and batch_exists
            and batch_n >= max(1, int(0.2 * len(gold)))
        ),
    }
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default="data/gold/gold_set.json")
    parser.add_argument("--human_batch", default="data/gold/human_review_batch.json")
    parser.add_argument("--min_n", type=int, default=150)
    args = parser.parse_args()
    print(json.dumps(validate_day5(args.gold, args.human_batch, args.min_n), ensure_ascii=False, indent=2))
