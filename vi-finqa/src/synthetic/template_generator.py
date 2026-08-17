"""Template-based synthetic generator.

Every kept sample is verified by executing pandas_query on a real evidence CSV.
No LLM required. Optional LLM paraphrase later.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yaml

from .sandbox import execute_inline


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
    "Chi phí khấu hao",
    "Thuế và các khoản phải nộp Nhà nước",
]

RATIO_PAIRS = [
    ("Tài sản ngắn hạn", "Tổng tài sản"),
    ("Nợ ngắn hạn", "Tổng tài sản"),
    ("LNST", "Doanh thu thuần"),
    ("Lợi nhuận trước thuế", "Doanh thu thuần"),
    ("Tiền và tương đương tiền", "Tài sản ngắn hạn"),
    ("Hàng tồn kho", "Tài sản ngắn hạn"),
]

SUM_PAIRS = [
    ("Tài sản ngắn hạn", "Tài sản dài hạn"),
    ("Nợ ngắn hạn", "Nợ dài hạn"),
    ("Tiền và tương đương tiền", "Hàng tồn kho"),
]

NOTE_METRICS = [
    "Chi phí khấu hao",
    "Thuế và các khoản phải nộp Nhà nước",
    "Chi phí nhân công",
    "Lợi nhuận sau thuế chưa phân phối",
    "Đầu tư tài chính ngắn hạn",
]


@dataclass
class SyntheticSample:
    question_id: str
    question: str
    category: str
    relevant_tables: list
    csv_path: str
    pandas_query: str
    answer: float | None
    verified: bool
    source_report_id: str


def load_taxonomy(path: str = "src/synthetic/taxonomy.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_mapped_index(
    long_path: str = "data/processed/long_format_mapped.jsonl",
    min_abs: float = 1000.0,
) -> Dict[Tuple[str, int, str], dict]:
    """(company, year, canonical) -> best row (largest abs value)."""
    idx: Dict[Tuple[str, int, str], dict] = {}
    p = Path(long_path)
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            can = r.get("canonical")
            co, y = r.get("company"), r.get("năm")
            if not can or not co or y is None:
                continue
            try:
                v = float(r["giá_trị"])
            except (TypeError, ValueError, KeyError):
                continue
            if abs(v) < min_abs:
                continue
            key = (str(co), int(y), str(can))
            prev = idx.get(key)
            if prev is None or abs(v) > abs(float(prev["giá_trị"])):
                idx[key] = r
    return idx


def _write_csv(qid: str, rows: List[dict], out_dir: Path) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    rel = f"data/synthetic/evidence/{qid}.csv"
    path = Path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")
    return rel.replace("\\", "/")


def _ref(row: dict) -> str:
    return f"{row.get('report_id','unk')}|{row.get('start_line', 0)}"


def _verify(item: dict) -> dict:
    try:
        val = execute_inline(item["pandas_query"], item["csv_path"])
        item["answer"] = float(val)
        item["verified"] = True
    except Exception:
        item["answer"] = None
        item["verified"] = False
    return item


def _qid(prefix: str, n: int) -> str:
    return f"{prefix}_{n:06d}"


def gen_lookup_simple(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    keys = [k for k in idx if k[2] in CORE_METRICS]
    rng.shuffle(keys)
    out = []
    i = start
    for co, y, can in keys:
        if len(out) >= n:
            break
        row = idx[(co, y, can)]
        qid = _qid("syn_lu", i)
        i += 1
        csv_path = _write_csv(qid, [row], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{can} của {co} năm {y} là bao nhiêu?",
            "category": "lookup_simple",
            "relevant_tables": [_ref(row)],
            "csv_path": csv_path,
            "pandas_query": (
                f"df[(df['canonical']=='{can}') & (df['năm']=={y}) & (df['company']=='{co}')]['giá_trị'].iloc[0]"
            ),
            "source_report_id": row.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_compare_2years(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    out = []
    i = start
    keys = list(idx.keys())
    rng.shuffle(keys)
    for co, y, can in keys:
        if len(out) >= n:
            break
        if can not in CORE_METRICS:
            continue
        prev = idx.get((co, y - 1, can))
        if not prev:
            continue
        a, b = idx[(co, y, can)], prev
        if abs(float(b["giá_trị"])) < 1:
            continue
        qid = _qid("syn_yoy", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{can} của {co} tăng bao nhiêu phần trăm từ năm {y-1} sang năm {y}?",
            "category": "compare_2years",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"(float(df[df['năm']=={y}]['giá_trị'].iloc[0]) - float(df[df['năm']=={y-1}]['giá_trị'].iloc[0])) "
                f"/ abs(float(df[df['năm']=={y-1}]['giá_trị'].iloc[0])) * 100"
            ),
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_yoy_abs(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    out, i = [], start
    keys = list(idx.keys())
    rng.shuffle(keys)
    for co, y, can in keys:
        if len(out) >= n:
            break
        if can not in CORE_METRICS:
            continue
        prev = idx.get((co, y - 1, can))
        if not prev:
            continue
        a, b = idx[(co, y, can)], prev
        qid = _qid("syn_yd", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{can} của {co} năm {y} tăng/giảm bao nhiêu so với năm {y-1}?",
            "category": "yoy_abs_diff",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"float(df[df['năm']=={y}]['giá_trị'].iloc[0]) - float(df[df['năm']=={y-1}]['giá_trị'].iloc[0])"
            ),
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_ratio(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    out, i = [], start
    cos_years = sorted({(k[0], k[1]) for k in idx})
    rng.shuffle(cos_years)
    for co, y in cos_years:
        if len(out) >= n:
            break
        pair = rng.choice(RATIO_PAIRS)
        a, b = idx.get((co, y, pair[0])), idx.get((co, y, pair[1]))
        if not a or not b:
            continue
        if abs(float(b["giá_trị"])) < 1:
            continue
        qid = _qid("syn_rt", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{pair[0]} chiếm bao nhiêu phần trăm {pair[1]} của {co} năm {y}?",
            "category": "ratio_structure",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"float(df[df['canonical']=='{pair[0]}']['giá_trị'].iloc[0]) / "
                f"float(df[df['canonical']=='{pair[1]}']['giá_trị'].iloc[0]) * 100"
            ),
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_financial_index(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    """Proxy ROE/ROA/margin from available mapped lines (not true avg equity)."""
    out, i = [], start
    formulas = [
        ("LNST", "Vốn chủ sở hữu", "ROE xấp xỉ (LNST / VCSH)"),
        ("LNST", "Tổng tài sản", "ROA xấp xỉ (LNST / Tổng tài sản)"),
        ("LNST", "Doanh thu thuần", "Biên LNST"),
        ("Lợi nhuận trước thuế", "Doanh thu thuần", "Biên lợi nhuận trước thuế"),
    ]
    cos_years = sorted({(k[0], k[1]) for k in idx})
    rng.shuffle(cos_years)
    for co, y in cos_years:
        if len(out) >= n:
            break
        num_k, den_k, label = rng.choice(formulas)
        a, b = idx.get((co, y, num_k)), idx.get((co, y, den_k))
        if not a or not b or abs(float(b["giá_trị"])) < 1:
            continue
        qid = _qid("syn_ix", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{label} của {co} năm {y} là bao nhiêu (đơn vị phần trăm)?",
            "category": "financial_index",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"float(df[df['canonical']=='{num_k}']['giá_trị'].iloc[0]) / "
                f"float(df[df['canonical']=='{den_k}']['giá_trị'].iloc[0]) * 100"
            ),
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_cagr(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    out, i = [], start
    keys = [(co, y, can) for (co, y, can) in idx if can in CORE_METRICS]
    rng.shuffle(keys)
    for co, y2, can in keys:
        if len(out) >= n:
            break
        y1 = y2 - 2
        a, b = idx.get((co, y2, can)), idx.get((co, y1, can))
        if not a or not b:
            continue
        start_v = float(b["giá_trị"])
        if start_v <= 0:
            continue
        qid = _qid("syn_cg", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"CAGR {can} của {co} giai đoạn {y1}-{y2} là bao nhiêu phần trăm?",
            "category": "multi_year_trend",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"(float(df[df['năm']=={y2}]['giá_trị'].iloc[0]) / "
                f"float(df[df['năm']=={y1}]['giá_trị'].iloc[0])) ** (1/2) - 1"
            ),
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_multi_table(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    out, i = [], start
    pairs = [
        ("Doanh thu thuần", "Tổng tài sản", "Vòng quay tổng tài sản (DT/TTS)"),
        ("Doanh thu thuần", "LNST", "Doanh thu thuần trừ LNST"),
        ("Nợ ngắn hạn", "Nợ dài hạn", "Tổng nợ"),
    ]
    cos_years = sorted({(k[0], k[1]) for k in idx})
    rng.shuffle(cos_years)
    for co, y in cos_years:
        if len(out) >= n:
            break
        a_k, b_k, label = rng.choice(pairs)
        a, b = idx.get((co, y, a_k)), idx.get((co, y, b_k))
        if not a or not b:
            continue
        qid = _qid("syn_mt", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        if "trừ" in label:
            pq = (
                f"float(df[df['canonical']=='{a_k}']['giá_trị'].iloc[0]) - "
                f"float(df[df['canonical']=='{b_k}']['giá_trị'].iloc[0])"
            )
        elif "Tổng nợ" in label:
            pq = (
                f"float(df[df['canonical']=='{a_k}']['giá_trị'].iloc[0]) + "
                f"float(df[df['canonical']=='{b_k}']['giá_trị'].iloc[0])"
            )
        else:
            if abs(float(b["giá_trị"])) < 1:
                continue
            pq = (
                f"float(df[df['canonical']=='{a_k}']['giá_trị'].iloc[0]) / "
                f"float(df[df['canonical']=='{b_k}']['giá_trị'].iloc[0])"
            )
        item = {
            "question_id": qid,
            "question": f"{label} của {co} năm {y} là bao nhiêu?",
            "category": "multi_table",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": pq,
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_compare_companies(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    bucket: Dict[Tuple[int, str], Dict[str, dict]] = defaultdict(dict)
    for (co, y, can), row in idx.items():
        if can not in ("Doanh thu thuần", "LNST", "Tổng tài sản", "Vốn chủ sở hữu", "Tài sản ngắn hạn"):
            continue
        bucket[(y, can)][co] = row
    out, i = [], start
    keys = list(bucket.keys())
    rng.shuffle(keys)
    for y, can in keys:
        if len(out) >= n:
            break
        cos = sorted(bucket[(y, can)].keys())
        if len(cos) < 2:
            continue
        a_co, b_co = rng.sample(cos, 2)
        ra, rb = bucket[(y, can)][a_co], bucket[(y, can)][b_co]
        qid = _qid("syn_cc", i)
        i += 1
        csv_path = _write_csv(qid, [ra, rb], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"Chênh lệch {can} giữa {a_co} và {b_co} năm {y} ({a_co} trừ {b_co}) là bao nhiêu?",
            "category": "compare_companies",
            "relevant_tables": list({_ref(ra), _ref(rb)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"float(df[df['company']=='{a_co}']['giá_trị'].iloc[0]) - "
                f"float(df[df['company']=='{b_co}']['giá_trị'].iloc[0])"
            ),
            "source_report_id": ra.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_notes(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    keys = [k for k in idx if k[2] in NOTE_METRICS]
    rng.shuffle(keys)
    out, i = [], start
    for co, y, can in keys:
        if len(out) >= n:
            break
        row = idx[(co, y, can)]
        qid = _qid("syn_nt", i)
        i += 1
        csv_path = _write_csv(qid, [row], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"Theo thuyết minh / chi tiết BCTC, {can} của {co} năm {y} là bao nhiêu?",
            "category": "notes_qa",
            "relevant_tables": [_ref(row)],
            "csv_path": csv_path,
            "pandas_query": (
                f"df[(df['canonical']=='{can}') & (df['năm']=={y}) & (df['company']=='{co}')]['giá_trị'].iloc[0]"
            ),
            "source_report_id": row.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_unit_round(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    keys = [k for k in idx if k[2] in CORE_METRICS]
    rng.shuffle(keys)
    out, i = [], start
    for co, y, can in keys:
        if len(out) >= n:
            break
        row = idx[(co, y, can)]
        qid = _qid("syn_ur", i)
        i += 1
        csv_path = _write_csv(qid, [row], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{can} của {co} năm {y} là bao nhiêu tỷ đồng (làm tròn 1 chữ số)?",
            "category": "unit_rounding",
            "relevant_tables": [_ref(row)],
            "csv_path": csv_path,
            "pandas_query": (
                f"round(float(df[(df['canonical']=='{can}') & (df['năm']=={y}) & (df['company']=='{co}')]['giá_trị'].iloc[0]) / 1e9, 1)"
            ),
            "source_report_id": row.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_negative(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    keys = [(k, idx[k]) for k in idx if float(idx[k]["giá_trị"]) < 0 and k[2] in CORE_METRICS + NOTE_METRICS]
    rng.shuffle(keys)
    out, i = [], start
    for (co, y, can), row in keys:
        if len(out) >= n:
            break
        qid = _qid("syn_ng", i)
        i += 1
        csv_path = _write_csv(qid, [row], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"{can} của {co} năm {y} có âm không, giá trị là bao nhiêu?",
            "category": "negative_edge_case",
            "relevant_tables": [_ref(row)],
            "csv_path": csv_path,
            "pandas_query": (
                f"float(df[(df['canonical']=='{can}') & (df['năm']=={y}) & (df['company']=='{co}')]['giá_trị'].iloc[0])"
            ),
            "source_report_id": row.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


def gen_sum_two(idx, rng: random.Random, start: int, n: int) -> List[dict]:
    out, i = [], start
    cos_years = sorted({(k[0], k[1]) for k in idx})
    rng.shuffle(cos_years)
    for co, y in cos_years:
        if len(out) >= n:
            break
        a_k, b_k = rng.choice(SUM_PAIRS)
        a, b = idx.get((co, y, a_k)), idx.get((co, y, b_k))
        if not a or not b:
            continue
        qid = _qid("syn_sm", i)
        i += 1
        csv_path = _write_csv(qid, [a, b], Path("data/synthetic/evidence"))
        item = {
            "question_id": qid,
            "question": f"Tổng {a_k} và {b_k} của {co} năm {y} là bao nhiêu?",
            "category": "sum_two_metrics",
            "relevant_tables": list({_ref(a), _ref(b)}),
            "csv_path": csv_path,
            "pandas_query": (
                f"float(df[df['canonical']=='{a_k}']['giá_trị'].iloc[0]) + "
                f"float(df[df['canonical']=='{b_k}']['giá_trị'].iloc[0])"
            ),
            "source_report_id": a.get("report_id", ""),
        }
        item = _verify(item)
        if item["verified"]:
            out.append(item)
    return out


PARAPHRASE_TEMPLATES = {
    "lookup_simple": [
        "Cho biết {q}",
        "Hỏi: {q}",
        "{q} (theo BCTC)",
        "Số liệu: {q}",
    ],
}


def paraphrase_rule_based(sample: dict, k: int, rng: random.Random) -> List[dict]:
    """Deterministic paraphrases — keep query/answer, change wording only."""
    q = sample["question"]
    variants = [
        q.replace("là bao nhiêu?", "đạt mức nào?"),
        q.replace("là bao nhiêu?", "bằng bao nhiêu đơn vị?"),
        "Xin cho biết " + q[0].lower() + q[1:] if q else q,
        q.replace("năm ", "niên độ "),
    ]
    out = []
    for j, nq in enumerate(variants[:k]):
        if nq == q:
            continue
        s = dict(sample)
        s["question"] = nq
        s["question_id"] = sample["question_id"] + f"_para{j}"
        s["verified"] = True
        out.append(s)
    return out


GENS = {
    "lookup_simple": gen_lookup_simple,
    "compare_2years": gen_compare_2years,
    "ratio_structure": gen_ratio,
    "financial_index": gen_financial_index,
    "multi_year_trend": gen_cagr,
    "multi_table": gen_multi_table,
    "compare_companies": gen_compare_companies,
    "notes_qa": gen_notes,
    "unit_rounding": gen_unit_round,
    "negative_edge_case": gen_negative,
    "yoy_abs_diff": gen_yoy_abs,
    "sum_two_metrics": gen_sum_two,
}


def generate_balanced(
    per_cat: int = 500,
    seed: int = 42,
    long_path: str = "data/processed/long_format_mapped.jsonl",
    paraphrase_k: int = 1,
) -> List[dict]:
    rng = random.Random(seed)
    idx = load_mapped_index(long_path)
    all_s: List[dict] = []
    for cat, fn in GENS.items():
        chunk = fn(idx, rng, start=1, n=per_cat)
        all_s.extend(chunk)
        if paraphrase_k:
            extra = []
            for s in chunk:
                extra.extend(paraphrase_rule_based(s, paraphrase_k, rng))
            all_s.extend(extra)
    return all_s
