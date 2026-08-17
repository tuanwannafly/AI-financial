"""Template ensemble without LLM: two query variants, vote if both exec."""
from __future__ import annotations

from collections import Counter

from ..synthetic.sandbox import execute_inline_code
from ..text2pandas.generator import template_pandas_code
from ..text2pandas.repair import sanity_check


def generate_ensemble(question, entities, csv_path) -> dict | None:
    codes = [
        template_pandas_code(question, entities),
        template_pandas_code(question, {**entities, "intent": "lookup"}),
    ]
    candidates = []
    for i, code in enumerate(codes):
        try:
            val = execute_inline_code(code, csv_path)
            if sanity_check(val):
                candidates.append({"strategy": f"t{i}", "value": round(float(val), 4), "code": code})
        except Exception:
            continue
    if not candidates:
        return None
    values = [c["value"] for c in candidates]
    most_common, n_agree = Counter(values).most_common(1)[0]
    chosen = next(c for c in candidates if c["value"] == most_common)
    return {**chosen, "n_agree": n_agree, "n_candidates": len(candidates)}
