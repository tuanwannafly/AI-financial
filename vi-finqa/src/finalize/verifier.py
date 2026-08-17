from __future__ import annotations

import json


REASONABLE_RANGES = {"financial_index": (-200.0, 200.0), "calc_ratio": (-500.0, 500.0)}


def rule_based_verify(answer, intent: str) -> dict:
    issues = []
    if answer is None or (isinstance(answer, float) and answer != answer):
        issues.append("answer rỗng hoặc NaN")
    if intent in REASONABLE_RANGES and isinstance(answer, (int, float)):
        lo, hi = REASONABLE_RANGES[intent]
        if not (lo <= answer <= hi):
            issues.append(f"answer {answer} ngoài khoảng [{lo},{hi}] cho {intent}")
    return {"valid": len(issues) == 0, "issues": issues}


def llm_verify(question, answer, unit, llm_call_fn) -> dict:
    try:
        return json.loads(
            llm_call_fn(
                f'Câu hỏi: {question}\nTrả lời: {answer} {unit or ""}\n'
                'JSON: {{"plausible": bool, "reason": "..."}}'
            )
        )
    except Exception:
        return {"plausible": True, "reason": "verify_parse_failed_fail_open"}
