from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


CATEGORIES = [
    "simple_lookup",
    "calculation",
    "multi_table",
    "company_compare",
    "thuyet_minh",
]


def verify_by_execution(item: Dict[str, Any]) -> Dict[str, Any]:
    """Execute pandas_query against evidence_csv; set answer + verified flag.

    Agent rule: NEVER let LLM invent the numeric answer — only execution.
    """
    import pandas as pd

    csv_path = item.get("evidence_csv") or item.get("csv_path")
    query = item.get("pandas_query")
    if not csv_path or not query:
        item["verified_by_execution"] = False
        item["exec_error"] = "missing evidence_csv or pandas_query"
        return item

    try:
        df = pd.read_csv(csv_path)
        result = eval(query, {"df": df, "pd": pd})
        item["answer"] = float(result) if result is not None else result
        item["verified_by_execution"] = True
        item.pop("exec_error", None)
    except Exception as e:
        item["verified_by_execution"] = False
        item["exec_error"] = str(e)
    return item


def export_human_review_batch(
    gold: List[Dict[str, Any]],
    out_path: str = "data/gold/human_review_batch.json",
    fraction: float = 0.2,
    seed: int = 42,
) -> dict:
    n = max(1, int(len(gold) * fraction))
    sample = random.Random(seed).sample(gold, min(n, len(gold)))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"n_gold": len(gold), "n_batch": len(sample), "out_path": out_path}


def category_balance_ok(gold: List[Dict[str, Any]]) -> bool:
    present = {g.get("category") for g in gold}
    return all(c in present for c in CATEGORIES)
