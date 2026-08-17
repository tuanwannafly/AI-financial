import json
import re
from collections import Counter
from pathlib import Path

OP_PATTERNS = {
    "lookup_simple": r"\.iloc\[0\]|\.loc\[",
    "pct_change": r"pct_change|/\s*abs\(",
    "ratio": r"/\s*float|/.*\*\s*100",
    "groupby": r"\.groupby\(",
    "merge_multi_table": r"\.merge\(|pd\.concat",
    "filter_year": r"\['năm'\]|year",
    "aggregation": r"\.sum\(\)|\.mean\(\)|\.agg\(",
}


def analyze_pandas_operations(queries: list[str]) -> dict:
    counts = Counter()
    for q in queries:
        for op, pattern in OP_PATTERNS.items():
            if re.search(pattern, q, re.IGNORECASE):
                counts[op] += 1
    return dict(counts)


def run_analysis() -> dict:
    gold = json.loads(Path("data/gold/gold_set.json").read_text(encoding="utf-8"))
    synth = []
    sp = Path("data/synthetic/verified_v1.jsonl")
    if sp.exists():
        with sp.open(encoding="utf-8") as f:
            synth = [json.loads(l) for l in f if l.strip()]
    qs = [g["pandas_query"] for g in gold if g.get("pandas_query")]
    qs += [s["pandas_query"] for s in synth if s.get("pandas_query")]
    return {"n_queries": len(qs), "ops": analyze_pandas_operations(qs)}


if __name__ == "__main__":
    print(json.dumps(run_analysis(), ensure_ascii=False, indent=2))
