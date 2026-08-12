from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .normalize import load_ontology, build_alias_index, normalize_term

LONG_KEYS = [
    "chỉ_tiêu",
    "năm",
    "giá_trị",
    "đơn_vị",
    "report_id",
    "start_line",
    "table_type",
    "company",
    "is_consolidated",
]

MAIN_TYPES = ("CDKT", "KQKD", "LCTT")

YEAR_HEADER_RE = re.compile(
    r"(?:31/12|01/01|N[aă]m|S[ốo] cu[ốo]i n[aă]m|S[ốo] [đd][ầu] n[aă]m)\s*((?:19|20)\d{2})",
    re.IGNORECASE,
)
DATE_YEAR_RE = re.compile(r"(\d{1,2})[\/\-.](\d{1,2})[\/\-.]((?:19|20)\d{2})")
NAM_YEAR_RE = re.compile(r"(?:N[aă]m|Year)\s*((?:19|20)\d{2})", re.IGNORECASE)
MIN_YEAR, MAX_YEAR = 2010, 2026

NAY_TRA = re.compile(r"n[aă]m nay|s[ốo] cu[ốo]i n[aă]m", re.IGNORECASE)
TRA = re.compile(r"n[aă]m trư[ớu]c|s[ốo] [đd][ầu] n[aă]m", re.IGNORECASE)
# date-as-number columns: 31/12/2015 -> current year, 01/01/2015 -> year-1
OPEN_DATE = re.compile(r"^\s*01/01", re.IGNORECASE)

UNIT_CELL_RE = re.compile(r"(VND|VNĐ|Triệu VND|tỷ đồng|triệu đồng|nghìn đồng|đồng)", re.IGNORECASE)


def _year_from_header(cell: str, record_year: Optional[int]) -> Optional[int]:
    m = YEAR_HEADER_RE.search(cell)
    if m:
        y = int(m.group(1))
        if not (MIN_YEAR <= y <= MAX_YEAR):
            return None
        # opening balance 01/01/YYYY refers to prior year end
        if OPEN_DATE.match(cell) and "N[aă]m" not in cell:
            return y - 1
        return y
    m = DATE_YEAR_RE.search(cell)
    if m:
        y = int(m.group(3))
        if not (MIN_YEAR <= y <= MAX_YEAR):
            return None
        if OPEN_DATE.match(m.group(0)):
            return y - 1
        return y
    m = NAM_YEAR_RE.search(cell)
    if m:
        y = int(m.group(1))
        return y if MIN_YEAR <= y <= MAX_YEAR else None
    if record_year is not None:
        if NAY_TRA.search(cell):
            return record_year
        if TRA.search(cell):
            return record_year - 1
    return None


def _cell_unit(cell: str) -> Optional[str]:
    m = UNIT_CELL_RE.search(cell)
    return m.group(1) if m else None


def detect_year_columns(
    rows: List[List[str]],
    record_year: Optional[int],
) -> Dict[int, Optional[int]]:
    """Map column index -> year for value columns (from header rows)."""
    mapping: Dict[int, Optional[int]] = {}
    for r in rows[:4]:
        for i, cell in enumerate(r):
            if i == 0:
                continue
            y = _year_from_header(cell, record_year)
            if y is not None and i not in mapping:
                mapping[i] = y
    return mapping


def _value(cell: str) -> Optional[float]:
    from ..extraction.table_extractor import normalize_number

    if not cell or cell.strip() in ("", "-", "--", "–"):
        return None
    return normalize_number(cell)


def longify_record(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = rec.get("rows") or []
    if not rows:
        return []
    if rec.get("table_type") not in MAIN_TYPES:
        return []

    record_year = rec.get("year")
    year_map = detect_year_columns(rows, record_year)
    if not year_map:
        return []

    unit = rec.get("unit")
    unit_from_cell = None
    for r in rows[:3]:
        for c in r:
            u = _cell_unit(c)
            if u:
                unit_from_cell = u
                break
        if unit_from_cell:
            break
    effective_unit = unit_from_cell or unit

    base = {
        "report_id": rec.get("report_id"),
        "start_line": rec.get("start_line"),
        "table_type": rec.get("table_type"),
        "company": rec.get("company"),
        "is_consolidated": rec.get("is_consolidated"),
        "đơn_vị": effective_unit,
    }

    # find index where data rows begin (after header rows containing years)
    start_idx = 0
    for i, r in enumerate(rows[:4]):
        if any(_year_from_header(c, record_year) is not None for c in r[1:]):
            start_idx = i + 1
            break
    if start_idx == 0:
        first = " ".join(rows[0])
        if re.search(r"m[ãa] s[ốo]|ch[ỉi] ti[êe]u|t[àa]i s[ảa]n|thuy[ếe]t minh", first, re.I):
            start_idx = 1

    out: List[Dict[str, Any]] = []
    for r in rows[start_idx:]:
        if not r or not r[0].strip():
            continue
        label = r[0].strip()
        if len(r) < 3:
            continue
        for col_idx, year in sorted(year_map.items()):
            if col_idx >= len(r):
                continue
            cell = r[col_idx]
            v = _value(cell)
            if v is None:
                continue
            row = {"chỉ_tiêu": label, "năm": year, "giá_trị": v}
            row.update(base)
            out.append(row)
    return out


def longify_all(records: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    for rec in records:
        yield from longify_record(rec)


def run_longify(
    metadata_path: str = "data/extracted/metadata.jsonl",
    out_path: str = "data/processed/long_format.jsonl",
) -> dict:
    src = Path(metadata_path)
    if not src.exists():
        return {"pass": False, "reason": "missing metadata"}
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    n_tables = 0
    n_rows = 0
    n_tables_with_long = 0
    years: set[int] = set()
    with src.open(encoding="utf-8") as f, out.open("w", encoding="utf-8") as w:
        for line in f:
            if not line.strip():
                continue
            n_tables += 1
            rec = json.loads(line)
            long_rows = longify_record(rec)
            if long_rows:
                n_tables_with_long += 1
            for r in long_rows:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
                n_rows += 1
                years.add(r["năm"])
    return {
        "n_tables_processed": n_tables,
        "n_tables_with_long": n_tables_with_long,
        "n_long_rows": n_rows,
        "n_years": len(years),
        "years_range": [min(years), max(years)] if years else None,
        "out_path": str(out),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", default="data/extracted/metadata.jsonl")
    parser.add_argument("--out", default="data/processed/long_format.jsonl")
    args = parser.parse_args()
    print(json.dumps(run_longify(args.metadata, args.out), ensure_ascii=False, indent=2))