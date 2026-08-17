from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def analyze_gold_distribution(gold_path: str = "data/gold/gold_set.json") -> dict:
    gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    by_cat = dict(Counter(g.get("category") for g in gold))
    by_co: Counter = Counter()
    by_year: Counter = Counter()
    for g in gold:
        meta = g.get("meta") or {}
        if meta.get("company"):
            by_co[meta["company"]] += 1
        if meta.get("companies"):
            for c in meta["companies"]:
                by_co[c] += 1
        if meta.get("year") is not None:
            by_year[str(meta["year"])] += 1
    return {
        "n_total": len(gold),
        "by_category": by_cat,
        "n_companies": len(by_co),
        "top_companies": by_co.most_common(15),
        "by_year": dict(sorted(by_year.items())),
        "verified": sum(1 for g in gold if g.get("verified_by_execution")),
    }


def analyze_long_coverage(long_path: str = "data/processed/long_format_mapped.jsonl", limit: int = 0) -> dict:
    p = Path(long_path)
    if not p.exists():
        return {"exists": False}
    by_can: Counter = Counter()
    by_co: Counter = Counter()
    by_year: Counter = Counter()
    n = 0
    n_mapped = 0
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            n += 1
            if r.get("canonical"):
                n_mapped += 1
                by_can[r["canonical"]] += 1
            if r.get("company"):
                by_co[r["company"]] += 1
            if r.get("năm") is not None:
                by_year[str(r["năm"])] += 1
            if limit and n >= limit:
                break
    return {
        "exists": True,
        "n_rows": n,
        "n_mapped": n_mapped,
        "n_companies": len(by_co),
        "top_canonical": by_can.most_common(20),
        "years": dict(sorted(by_year.items())),
    }


if __name__ == "__main__":
    out = {
        "gold": analyze_gold_distribution(),
        "long": analyze_long_coverage(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
