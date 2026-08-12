"""Day 5 gold set builder.

Rules:
- Answer ONLY from executing pandas_query on evidence CSV (never LLM-invented numbers).
- ≥150 questions across 5 categories.
- Export ~20% human_review_batch.json.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .build_gold_helpers import (
    CATEGORIES,
    export_human_review_batch,
    verify_by_execution,
)

# Prefer these canonical metrics for clean gold
CORE_METRICS = [
    "Doanh thu thuần",
    "LNST",
    "Lợi nhuận trước thuế",
    "Tài sản ngắn hạn",
    "Tài sản dài hạn",
    "Tổng tài sản",
    "Nợ ngắn hạn",
    "Nợ dài hạn",
    "Vốn chủ sở hữu",
    "Tiền và tương đương tiền",
    "Hàng tồn kho",
    "Phải thu ngắn hạn",
    "Chi phí tài chính",
    "Chi phí quản lý doanh nghiệp",
    "Chi phí bán hàng",
    "Lưu chuyển tiền thuần từ HĐKD",
]


def load_long(path: str = "data/processed/long_format_mapped.jsonl") -> List[dict]:
    rows = []
    p = Path(path)
    if not p.exists():
        # fallback unmapped
        p = Path("data/processed/long_format.jsonl")
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def _safe_qid(i: int) -> str:
    return f"q_{i:04d}"


def _unit_label(u: Optional[str]) -> str:
    if not u:
        return "VND"
    if re.search(r"triệu", u, re.I):
        return "triệu đồng"
    if re.search(r"tỷ", u, re.I):
        return "tỷ đồng"
    if re.search(r"nghìn", u, re.I):
        return "nghìn đồng"
    return "VND"


def _write_evidence(qid: str, rows: List[dict], evidence_dir: Path) -> str:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    rel = f"data/gold/evidence/{qid}.csv"
    path = Path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    # enforce long schema columns present
    for col in ["chỉ_tiêu", "năm", "giá_trị", "đơn_vị", "report_id", "start_line", "table_type", "company", "is_consolidated"]:
        if col not in df.columns:
            df[col] = None
    if "canonical" not in df.columns:
        df["canonical"] = None
    df.to_csv(path, index=False, encoding="utf-8")
    return rel.replace("\\", "/")


def _table_ref(row: dict) -> str:
    rid = row.get("report_id") or "unknown"
    sl = row.get("start_line")
    if sl is None:
        return rid
    return f"{rid}|{sl}"


def _doc_id(row: dict) -> str:
    return row.get("report_id") or "unknown"


def build_simple_lookup(rows: List[dict], start_id: int, target: int = 50) -> List[dict]:
    """Pick single-cell lookups from mapped core metrics."""
    by_key: Dict[Tuple, list] = defaultdict(list)
    for r in rows:
        can = r.get("canonical")
        if can not in CORE_METRICS:
            continue
        if r.get("giá_trị") is None or r.get("năm") is None or not r.get("company"):
            continue
        # prefer absolute values that look like money (not tiny ma-so leftovers)
        v = abs(float(r["giá_trị"]))
        if v < 1000:
            continue
        key = (r["company"], r["năm"], can, r.get("is_consolidated"), r.get("report_id"))
        by_key[key].append(r)

    items = []
    qid_n = start_id
    # stable sort keys
    keys = sorted(by_key.keys(), key=lambda k: (k[0], k[1], k[2]))
    seen = set()
    for key in keys:
        if len(items) >= target:
            break
        company, year, can, cons, rid = key
        if (company, year, can, cons) in seen:
            continue
        candidates = by_key[key]
        # pick largest abs value row (main total more likely)
        row = max(candidates, key=lambda x: abs(float(x["giá_trị"])))
        seen.add((company, year, can, cons))

        qid = _safe_qid(qid_n)
        qid_n += 1
        evidence_rows = [row]
        csv_path = _write_evidence(qid, evidence_rows, Path("data/gold/evidence"))
        cons_txt = "hợp nhất" if cons else "riêng"
        unit = _unit_label(row.get("đơn_vị"))
        question = (
            f"{can} của {company} năm {year} "
            f"(BCTC {cons_txt}) là bao nhiêu {unit}?"
        )
        pandas_query = (
            f"df[(df['canonical']=='{can}') & (df['năm']=={year}) & (df['company']=='{company}')]"
            f"['giá_trị'].iloc[0]"
        )
        item = {
            "question_id": qid,
            "question": question,
            "category": "simple_lookup",
            "relevant_docs": [_doc_id(row)],
            "relevant_tables": [_table_ref(row)],
            "evidence_csv": csv_path,
            "csv_path": csv_path,
            "pandas_query": pandas_query,
            "unit": unit,
            "meta": {"company": company, "year": year, "canonical": can},
        }
        item = verify_by_execution(item)
        if item.get("verified_by_execution"):
            items.append(item)
    return items


def build_calculation(rows: List[dict], start_id: int, target: int = 30) -> List[dict]:
    """YoY change or sum of two lines within same company-year."""
    # index: company, year, can -> best row
    idx: Dict[Tuple[str, int, str], dict] = {}
    for r in rows:
        can = r.get("canonical")
        if can not in CORE_METRICS:
            continue
        co, y = r.get("company"), r.get("năm")
        if not co or y is None:
            continue
        v = abs(float(r["giá_trị"]))
        if v < 1000:
            continue
        key = (co, int(y), can)
        prev = idx.get(key)
        if prev is None or abs(float(r["giá_trị"])) > abs(float(prev["giá_trị"])):
            idx[key] = r

    items = []
    qid_n = start_id
    # YoY pairs
    for (co, y, can), row in sorted(idx.items()):
        if len(items) >= target:
            break
        prev = idx.get((co, y - 1, can))
        if not prev:
            continue
        if abs(float(prev["giá_trị"])) < 1:
            continue
        qid = _safe_qid(qid_n)
        qid_n += 1
        evidence = [row, prev]
        csv_path = _write_evidence(qid, evidence, Path("data/gold/evidence"))
        unit = _unit_label(row.get("đơn_vị"))
        question = (
            f"{can} của {co} năm {y} tăng/giảm bao nhiêu {unit} so với năm {y-1}?"
        )
        pandas_query = (
            f"float(df[df['năm']=={y}]['giá_trị'].iloc[0]) - float(df[df['năm']=={y-1}]['giá_trị'].iloc[0])"
        )
        item = {
            "question_id": qid,
            "question": question,
            "category": "calculation",
            "relevant_docs": list({_doc_id(row), _doc_id(prev)}),
            "relevant_tables": list({_table_ref(row), _table_ref(prev)}),
            "evidence_csv": csv_path,
            "csv_path": csv_path,
            "pandas_query": pandas_query,
            "unit": unit,
            "meta": {"company": co, "year": y, "canonical": can, "op": "yoy_diff"},
        }
        item = verify_by_execution(item)
        if item.get("verified_by_execution"):
            items.append(item)
    return items


def build_multi_table(rows: List[dict], start_id: int, target: int = 25) -> List[dict]:
    """Combine two different metrics (e.g. TSNH + TSDH or DT + LNST) same company-year."""
    pairs = [
        ("Tài sản ngắn hạn", "Tài sản dài hạn", "Tổng tài sản ngắn hạn + dài hạn"),
        ("Doanh thu thuần", "LNST", "Doanh thu thuần và LNST (hiệu số)"),
        ("Nợ ngắn hạn", "Nợ dài hạn", "Tổng nợ ngắn hạn + dài hạn"),
        ("Tiền và tương đương tiền", "Hàng tồn kho", "Tiền + Hàng tồn kho"),
    ]
    idx: Dict[Tuple[str, int, str], dict] = {}
    for r in rows:
        can = r.get("canonical")
        if not can:
            continue
        co, y = r.get("company"), r.get("năm")
        if not co or y is None:
            continue
        if abs(float(r["giá_trị"])) < 1000:
            continue
        key = (co, int(y), can)
        prev = idx.get(key)
        if prev is None or abs(float(r["giá_trị"])) > abs(float(prev["giá_trị"])):
            idx[key] = r

    items = []
    qid_n = start_id
    for co_y_can, row in sorted(idx.items()):
        if len(items) >= target:
            break
        co, y, can = co_y_can
        for a, b, label in pairs:
            if can != a:
                continue
            other = idx.get((co, y, b))
            if not other:
                continue
            # same report preferred but not required
            qid = _safe_qid(qid_n)
            qid_n += 1
            evidence = [row, other]
            csv_path = _write_evidence(qid, evidence, Path("data/gold/evidence"))
            unit = _unit_label(row.get("đơn_vị"))
            if "hiệu số" in label:
                question = f"{label} của {co} năm {y} là bao nhiêu {unit}?"
                pandas_query = (
                    f"float(df[df['canonical']=='{a}']['giá_trị'].iloc[0]) - "
                    f"float(df[df['canonical']=='{b}']['giá_trị'].iloc[0])"
                )
            else:
                question = f"{label} của {co} năm {y} là bao nhiêu {unit}?"
                pandas_query = (
                    f"float(df[df['canonical']=='{a}']['giá_trị'].iloc[0]) + "
                    f"float(df[df['canonical']=='{b}']['giá_trị'].iloc[0])"
                )
            item = {
                "question_id": qid,
                "question": question,
                "category": "multi_table",
                "relevant_docs": list({_doc_id(row), _doc_id(other)}),
                "relevant_tables": list({_table_ref(row), _table_ref(other)}),
                "evidence_csv": csv_path,
                "csv_path": csv_path,
                "pandas_query": pandas_query,
                "unit": unit,
                "meta": {"company": co, "year": y, "pair": [a, b]},
            }
            item = verify_by_execution(item)
            if item.get("verified_by_execution"):
                items.append(item)
            if len(items) >= target:
                break
    return items


def build_company_compare(rows: List[dict], start_id: int, target: int = 25) -> List[dict]:
    """Compare same metric across two companies same year."""
    # (year, can) -> company -> row
    bucket: Dict[Tuple[int, str], Dict[str, dict]] = defaultdict(dict)
    for r in rows:
        can = r.get("canonical")
        if can not in ("Doanh thu thuần", "LNST", "Tổng tài sản", "Vốn chủ sở hữu", "Tài sản ngắn hạn"):
            continue
        co, y = r.get("company"), r.get("năm")
        if not co or y is None:
            continue
        if abs(float(r["giá_trị"])) < 1000:
            continue
        key = (int(y), can)
        prev = bucket[key].get(co)
        if prev is None or abs(float(r["giá_trị"])) > abs(float(prev["giá_trị"])):
            bucket[key][co] = r

    items = []
    qid_n = start_id
    for (y, can), co_map in sorted(bucket.items()):
        companies = sorted(co_map.keys())
        if len(companies) < 2:
            continue
        for i in range(len(companies) - 1):
            if len(items) >= target:
                break
            a, b = companies[i], companies[i + 1]
            ra, rb = co_map[a], co_map[b]
            qid = _safe_qid(qid_n)
            qid_n += 1
            evidence = [ra, rb]
            csv_path = _write_evidence(qid, evidence, Path("data/gold/evidence"))
            unit = _unit_label(ra.get("đơn_vị"))
            question = (
                f"{can} của {a} so với {b} năm {y} chênh lệch bao nhiêu {unit} "
                f"({a} − {b})?"
            )
            pandas_query = (
                f"float(df[df['company']=='{a}']['giá_trị'].iloc[0]) - "
                f"float(df[df['company']=='{b}']['giá_trị'].iloc[0])"
            )
            item = {
                "question_id": qid,
                "question": question,
                "category": "company_compare",
                "relevant_docs": list({_doc_id(ra), _doc_id(rb)}),
                "relevant_tables": list({_table_ref(ra), _table_ref(rb)}),
                "evidence_csv": csv_path,
                "csv_path": csv_path,
                "pandas_query": pandas_query,
                "unit": unit,
                "meta": {"companies": [a, b], "year": y, "canonical": can},
            }
            item = verify_by_execution(item)
            if item.get("verified_by_execution"):
                items.append(item)
        if len(items) >= target:
            break
    return items


def build_thuyet_minh(rows: List[dict], start_id: int, target: int = 25) -> List[dict]:
    """Lookup from note-style metrics / non-main tables if available; else detailed line items."""
    # Prefer rows with table_type THUYET_MINH — longify currently only MAIN_TYPES.
    # Use detailed line items (chi phí khấu hao, thuế, etc.) as proxy for note lookups.
    note_metrics = [
        "Chi phí khấu hao",
        "Thuế và các khoản phải nộp Nhà nước",
        "Chi phí nhân công",
        "Lợi nhuận sau thuế chưa phân phối",
        "Đầu tư tài chính ngắn hạn",
    ]
    by_key: Dict[Tuple, list] = defaultdict(list)
    for r in rows:
        can = r.get("canonical")
        if can not in note_metrics:
            continue
        if r.get("giá_trị") is None or r.get("năm") is None or not r.get("company"):
            continue
        if abs(float(r["giá_trị"])) < 100:
            continue
        key = (r["company"], r["năm"], can)
        by_key[key].append(r)

    items = []
    qid_n = start_id
    for key in sorted(by_key.keys()):
        if len(items) >= target:
            break
        company, year, can = key
        row = max(by_key[key], key=lambda x: abs(float(x["giá_trị"])))
        qid = _safe_qid(qid_n)
        qid_n += 1
        csv_path = _write_evidence(qid, [row], Path("data/gold/evidence"))
        unit = _unit_label(row.get("đơn_vị"))
        question = (
            f"Theo thuyết minh / chi tiết BCTC, {can} của {company} năm {year} "
            f"là bao nhiêu {unit}?"
        )
        pandas_query = (
            f"df[(df['canonical']=='{can}') & (df['năm']=={year}) & (df['company']=='{company}')]"
            f"['giá_trị'].iloc[0]"
        )
        item = {
            "question_id": qid,
            "question": question,
            "category": "thuyet_minh",
            "relevant_docs": [_doc_id(row)],
            "relevant_tables": [_table_ref(row)],
            "evidence_csv": csv_path,
            "csv_path": csv_path,
            "pandas_query": pandas_query,
            "unit": unit,
            "meta": {"company": company, "year": year, "canonical": can, "note_proxy": True},
        }
        item = verify_by_execution(item)
        if item.get("verified_by_execution"):
            items.append(item)
    return items


def build_gold_set(
    long_path: str = "data/processed/long_format_mapped.jsonl",
    out_path: str = "data/gold/gold_set.json",
    min_n: int = 150,
) -> dict:
    rows = load_long(long_path)
    gold: List[dict] = []

    # targets sum >= 150 with balance
    simple = build_simple_lookup(rows, start_id=1, target=50)
    gold.extend(simple)
    calc = build_calculation(rows, start_id=len(gold) + 1, target=30)
    gold.extend(calc)
    multi = build_multi_table(rows, start_id=len(gold) + 1, target=25)
    gold.extend(multi)
    compare = build_company_compare(rows, start_id=len(gold) + 1, target=25)
    gold.extend(compare)
    notes = build_thuyet_minh(rows, start_id=len(gold) + 1, target=30)
    gold.extend(notes)

    # top up simple_lookup if still short
    if len(gold) < min_n:
        extra = build_simple_lookup(rows, start_id=len(gold) + 1, target=min_n - len(gold) + 20)
        # avoid duplicate question text
        seen_q = {g["question"] for g in gold}
        for e in extra:
            if e["question"] not in seen_q:
                gold.append(e)
                seen_q.add(e["question"])
            if len(gold) >= min_n:
                break

    # renumber question_ids sequentially
    for i, g in enumerate(gold, start=1):
        g["question_id"] = _safe_qid(i)

    # only keep verified
    gold = [g for g in gold if g.get("verified_by_execution") is True]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")

    batch_stats = export_human_review_batch(gold, fraction=0.2, seed=42)

    from collections import Counter

    cats = Counter(g["category"] for g in gold)
    return {
        "n_gold": len(gold),
        "categories": dict(cats),
        "n_verified": sum(1 for g in gold if g.get("verified_by_execution")),
        "out_path": out_path,
        "human_review_batch": batch_stats,
        "categories_ok": all(c in cats for c in CATEGORIES),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--long", default="data/processed/long_format_mapped.jsonl")
    parser.add_argument("--out", default="data/gold/gold_set.json")
    parser.add_argument("--min_n", type=int, default=150)
    args = parser.parse_args()
    stats = build_gold_set(args.long, args.out, args.min_n)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
