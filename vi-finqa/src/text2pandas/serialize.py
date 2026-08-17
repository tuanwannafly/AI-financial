from __future__ import annotations

import json


def serialize_structured_text(table: dict, ontology_alias_index: dict | None = None) -> str:
    parts = [
        f"Công ty: {table.get('company','')}",
        f"Năm: {table.get('year','')}",
        f"Loại bảng: {table.get('table_type','')}",
        f"Đơn vị: {table.get('unit','')}",
    ]
    alias = ontology_alias_index or {}
    for row in table.get("rows", [])[:15]:
        if row and row[0]:
            canon = alias.get(str(row[0]).lower())
            parts.append(str(row[0]) + (f" ({canon})" if canon and canon != row[0] else ""))
    return " | ".join(parts)


def serialize_markdown_table(table: dict) -> str:
    cols = table.get("columns") or ["chỉ_tiêu", "giá_trị"]
    header = "| " + " | ".join(map(str, cols)) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for r in table.get("rows", [])[:15]:
        if isinstance(r, dict):
            rows.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
        else:
            rows.append("| " + " | ".join(map(str, r)) + " |")
    return "\n".join([header, sep] + rows)


def serialize_compact_json(table: dict) -> str:
    return json.dumps(
        {
            "columns": table.get("columns", []),
            "rows": table.get("rows", [])[:15],
            "unit": table.get("unit"),
            "company": table.get("company"),
            "year": table.get("year"),
        },
        ensure_ascii=False,
    )


def serialize_relevant_columns_only(table: dict, financial_terms: list[str] | None = None) -> str:
    terms = [t.lower() for t in (financial_terms or [])]
    rows = table.get("rows", [])
    if terms:
        filtered = []
        for r in rows:
            label = str(r[0] if isinstance(r, list) else r.get("chỉ_tiêu") or r.get("canonical") or "")
            if any(t in label.lower() for t in terms):
                filtered.append(r)
        rows = filtered or rows[:15]
    else:
        rows = rows[:15]
    return serialize_markdown_table({**table, "rows": rows})
