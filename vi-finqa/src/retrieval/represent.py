from __future__ import annotations


def build_table_document(table_meta: dict, rows: list, ontology_alias_index: dict) -> str:
    parts = [
        f"Công ty: {table_meta.get('company','')}",
        f"Năm: {table_meta.get('year','')}",
        f"Loại bảng: {table_meta.get('table_type','')}",
        f"Đơn vị: {table_meta.get('unit','')}",
    ]
    for row in (rows or [])[:15]:
        if row and row[0]:
            term = str(row[0])
            canon = ontology_alias_index.get(term.lower())
            parts.append(term + (f" ({canon})" if canon and canon != term else ""))
    return " | ".join(parts)


def build_doc_from_long_cluster(rows: list[dict], ontology_alias_index: dict | None = None) -> str:
    if not rows:
        return ""
    r0 = rows[0]
    parts = [
        f"Công ty: {r0.get('company','')}",
        f"Năm: {r0.get('năm','')}",
        f"Loại bảng: {r0.get('table_type','')}",
        f"Đơn vị: {r0.get('đơn_vị','')}",
        f"report: {r0.get('report_id','')}",
    ]
    seen = set()
    for r in rows[:40]:
        term = r.get("canonical") or r.get("chỉ_tiêu") or ""
        raw = r.get("chỉ_tiêu") or ""
        if term and term not in seen:
            seen.add(term)
            parts.append(str(term))
        if raw and raw not in seen:
            seen.add(raw)
            parts.append(str(raw))
    return " | ".join(parts)
