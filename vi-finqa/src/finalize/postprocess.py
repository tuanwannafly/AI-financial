from __future__ import annotations

import re


def normalize_unit_answer(value: float, table_unit: str | None, target_unit: str = "tỷ đồng") -> float:
    scale = {"triệu": 1e6, "tỷ": 1e9, "nghìn": 1e3, "đồng": 1}
    target_scale = {"tỷ đồng": 1e9, "triệu đồng": 1e6, "VND": 1, "đồng": 1}
    if not table_unit:
        return value
    src = 1.0
    for k, s in scale.items():
        if k in table_unit.lower():
            src = s
            break
    return (value * src) / target_scale.get(target_unit, 1)


def round_answer(value: float, decimals: int = 2) -> float:
    return round(float(value), decimals)


def suggest_nearest_columns(error_msg: str, available_columns: list[str]) -> str:
    from rapidfuzz import process

    m = re.search(r"'(.+?)'", error_msg)
    if not m:
        return ""
    matches = process.extract(m.group(1), available_columns, limit=3)
    return f"Cột '{m.group(1)}' không tồn tại. Cột gần nhất: {[x[0] for x in matches]}"


def check_year_availability(entities: dict, table_meta: dict) -> str | None:
    if entities.get("years") and table_meta.get("year") not in entities["years"]:
        return (
            f"Câu hỏi hỏi năm {entities['years']}, bảng meta năm {table_meta.get('year')} — "
            "không đoán số từ năm khác."
        )
    return None


def check_notes_qa_format(gold_set: list[dict]) -> dict:
    notes = [g for g in gold_set if g.get("category") in ("notes_qa", "thuyet_minh")]
    numeric = sum(1 for g in notes if isinstance(g.get("answer"), (int, float)))
    return {"n_notes_qa": len(notes), "numeric_answer_ratio": numeric / len(notes) if notes else None}
