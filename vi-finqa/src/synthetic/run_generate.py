from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import List

from .template_generator import generate_balanced, load_taxonomy
from .sandbox import execute_inline


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def dedup_questions(samples: List[dict], threshold: float = 0.92) -> List[dict]:
    keep = []
    qs = []
    for s in samples:
        q = s["question"]
        if any(jaccard(q, k) >= threshold for k in qs):
            continue
        keep.append(s)
        qs.append(q)
    return keep


def check_distribution(samples: List[dict], taxonomy: dict, min_ratio: float = 0.05) -> dict:
    counts = Counter(s["category"] for s in samples)
    total = len(samples)
    under = [c for c in taxonomy if total and counts.get(c, 0) / total < min_ratio]
    return {"counts": dict(counts), "underrepresented": under, "n": total}


def write_jsonl(path: str, rows: List[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run(
    per_cat: int = 450,
    paraphrase_k: int = 1,
    target: int = 5000,
    seed: int = 42,
    out_path: str = "data/synthetic/verified_v1.jsonl",
    holdout_path: str = "data/synthetic/holdout_val.jsonl",
    holdout_frac: float = 0.1,
) -> dict:
    tax = load_taxonomy()
    samples = generate_balanced(per_cat=per_cat, seed=seed, paraphrase_k=paraphrase_k)
    verified = [s for s in samples if s.get("verified")]
    n_before_dedup = len(verified)
    verified = dedup_questions(verified, threshold=0.92)
    dup_rate = 1 - (len(verified) / n_before_dedup) if n_before_dedup else 0.0

    dist = check_distribution(verified, tax, min_ratio=0.05)
    # if underrepresented and we have headroom, already generated per_cat — report only

    rng = random.Random(seed + 7)
    rng.shuffle(verified)
    n_hold = max(1, int(len(verified) * holdout_frac))
    holdout = verified[:n_hold]
    train = verified[n_hold:]

    write_jsonl(out_path, train)
    write_jsonl(holdout_path, holdout)

    # pilot review batch
    review = rng.sample(train, min(80, len(train)))
    Path("data/synthetic/pilot_review_batch.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "n_generated_verified": n_before_dedup,
        "n_after_dedup": len(verified),
        "dup_rate": dup_rate,
        "n_train": len(train),
        "n_holdout": len(holdout),
        "distribution": dist,
        "target_met": len(verified) >= target,
        "out_path": out_path,
        "holdout_path": holdout_path,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--per-cat", type=int, default=450)
    parser.add_argument("--para", type=int, default=1)
    parser.add_argument("--target", type=int, default=5000)
    args = parser.parse_args()
    print(json.dumps(run(per_cat=args.per_cat, paraphrase_k=args.para, target=args.target), ensure_ascii=False, indent=2))
