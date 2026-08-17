from __future__ import annotations

import math
import re

from ..synthetic.sandbox import execute_inline_code
from .generator import extract_code_block, template_pandas_code


def shorten_traceback(err: str, max_lines: int = 3) -> str:
    return "\n".join(str(err).strip().splitlines()[-max_lines:])


def sanity_check(value) -> bool:
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and math.isnan(value))
    if isinstance(value, (list, tuple)):
        return len(value) > 0 and all(isinstance(v, (int, float)) for v in value)
    return False


def _rule_repair(code: str, error: str, entities: dict | None) -> str:
    """Deterministic repairs when no LLM: KeyError column / missing answer / iloc."""
    if "KeyError" in error and "canonical" in error:
        return code.replace("['canonical']", "['chỉ_tiêu']")
    if "KeyError" in error and "năm" in error:
        return code.replace("['năm']", "['year']") if "year" not in code else code
    if "iloc" in error.lower() or "index" in error.lower():
        return "answer = float(df['giá_trị'].dropna().iloc[0])"
    if entities:
        return template_pandas_code("", {**entities, "intent": entities.get("intent", "lookup")})
    return code


def self_repair(
    question,
    table_desc,
    code,
    csv_path,
    llm_call_fn=None,
    max_attempts: int = 4,
    entities: dict | None = None,
) -> dict:
    current_code = code
    log = []
    for attempt in range(max_attempts):
        try:
            value = execute_inline_code(current_code, csv_path)
            status = "ok"
        except Exception as e:
            status, value = "error", str(e)
        log.append({"attempt": attempt, "status": status})
        if status == "ok" and sanity_check(value):
            return {"success": True, "code": current_code, "value": value, "attempts": log}
        error_msg = str(value) if status == "error" else "Timeout/invalid"
        if llm_call_fn:
            prompt = (
                f"Sửa pandas. Câu: {question}\nBảng: {table_desc[:400]}\n"
                f"Code:\n```python\n{current_code}\n```\nLỗi: {shorten_traceback(error_msg)}"
            )
            current_code = extract_code_block(llm_call_fn(prompt))
        else:
            current_code = _rule_repair(current_code, error_msg, entities)
    return {"success": False, "code": current_code, "attempts": log, "value": None}
