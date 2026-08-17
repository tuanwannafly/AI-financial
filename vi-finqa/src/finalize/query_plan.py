"""Grounded query planning helpers for the official submission pack.

The public question release contains many labels that are not present in the
small ontology used by the synthetic evaluation.  This module deliberately
works from the complete long-format corpus and keeps all numeric operations
grounded in rows that are copied into the submission evidence CSV.
"""
from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from typing import Any, Iterable

from rapidfuzz import fuzz, process


MOJIBAKE_MARKERS = ("Ã", "Â", "Ä", "Å", "á", "â", "ð", "�")
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
TICKER_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2,5})(?![A-Z0-9])")

RAW_LABEL = "chỉ_tiêu"
RAW_YEAR = "năm"
RAW_VALUE = "giá_trị"
RAW_UNIT = "đơn_vị"

GENERIC_METRIC_LABELS = {
    "a",
    "b",
    "c",
    "d",
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "cong",
    "tong",
    "cong cong",
}
CODE_ONLY_LABEL_RE = re.compile(r"^(?:[a-z]+|\d+[a-z]?)$", re.IGNORECASE)
COMPANY_NOISE_HINTS = (
    "cong ty",
    "ctcp",
    "ngan hang",
    "tap doan",
    "tong cong ty",
    "doanh nghiep",
    "chi nhanh",
)
FINANCIAL_LABEL_HINTS = (
    "doanh thu",
    "chi phi",
    "loi nhuan",
    "tai san",
    "no phai tra",
    "von chu",
    "tien",
    "co phieu",
    "lai",
    "hang ton",
    "phai thu",
    "phai tra",
    "khau hao",
    "du phong",
    "thue",
    "thu nhap",
    "dau tu",
    "tai chinh",
    "kinh doanh",
    "bien dong",
    "gia von",
    "ban hang",
    "cung cap",
    "quy",
    "luu chuyen",
    "hoat dong",
    "hang hoa",
    "gia tri",
    "he so",
    "ty le",
    "cho vay",
    "du no",
    "khoan vay",
    "vay",
    "so du",
    "so tien",
    "nghia vu",
    "thu",
    "phat",
    "xay dung",
    "do dang",
)
QUERY_STOPWORDS = {
    "la",
    "bao",
    "nhieu",
    "nam",
    "cuoi",
    "dau",
    "ky",
    "ngay",
    "thang",
    "den",
    "trong",
    "cua",
    "cho",
    "voi",
    "va",
    "hoac",
    "tai",
    "tu",
    "so",
    "du",
    "muc",
    "gia",
    "tri",
    "dong",
    "tien",
    "don",
    "vi",
    "tinh",
    "theo",
    "cong",
    "ty",
    "me",
}


def repair_mojibake(value: Any) -> str:
    """Return a stable string for both UTF-8 and the released mojibake text."""
    text = "" if value is None else str(value)
    for _ in range(2):
        if not any(marker in text for marker in MOJIBAKE_MARKERS):
            break
        try:
            candidate = text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        old_score = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
        new_score = sum(candidate.count(marker) for marker in MOJIBAKE_MARKERS)
        if new_score >= old_score:
            break
        text = candidate
    return text


def normalized_text(value: Any) -> str:
    text = repair_mojibake(value)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower().replace("đ", "d")
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_usable_metric_label(value: Any) -> bool:
    """Reject section markers and note prose before retrieval sees them.

    OCR tables contain many numeric/code rows (``A-``, ``C.``, ``01``) and
    explanatory rows containing company names.  Treating those as metrics
    makes fuzzy matching select arbitrary evidence for difficult questions.
    """
    key = normalized_text(value)
    if len(key) < 4 or key in {"nan", "none"}:
        return False
    if key in GENERIC_METRIC_LABELS or CODE_ONLY_LABEL_RE.fullmatch(key):
        return False
    if re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", key):
        return False
    if any(hint in key for hint in COMPANY_NOISE_HINTS):
        return False
    tokens = [token for token in key.split() if token]
    if not any(len(token) >= 3 and re.search(r"[a-z]", token) for token in tokens):
        return False
    # Short non-financial headings (e.g. ``Thương mại``, ``Hàng không`` or
    # ``Ngắn hạn``) appear frequently in notes and otherwise become false
    # metric matches when a question mentions a sector or a time qualifier.
    return any(hint in key for hint in FINANCIAL_LABEL_HINTS) or len(tokens) > 5


def parse_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "—", "–", "na", "n/a"}:
        return 0.0 if text in {"-", "—", "–"} else None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("() ").replace(" ", "").replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def load_company_aliases(path: str = "data/raw/code_stock.csv") -> dict[str, str]:
    """Map every normalized ticker/name alias to the ticker used in long data."""
    aliases: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 2:
                    continue
                ticker, name = str(row[0]).strip().upper(), str(row[1]).strip()
                if not re.fullmatch(r"[A-Z]{2,5}", ticker):
                    continue
                aliases[normalized_text(ticker)] = ticker
                aliases[normalized_text(name)] = ticker
    except FileNotFoundError:
        pass
    return aliases


def detect_scope(question: str) -> str:
    q = normalized_text(question)
    if any(x in q for x in ("cong ty me", "bctc rieng", "bao cao rieng", " rieng")):
        return "separate"
    if any(x in q for x in ("hop nhat", "bctc hop nhat", "bao cao hop nhat")):
        return "consolidated"
    return "any"


def target_unit(question: str) -> tuple[str, float]:
    q = normalized_text(question)
    if "nghin ty" in q:
        return "nghìn tỷ", 1e12
    if "tram ty" in q:
        return "trăm tỷ", 1e11
    if "trieu" in q:
        return "triệu đồng", 1e6
    if any(pattern in q for pattern in ("ty dong", "ty vnd", "tinh bang ty", "don vi ty")):
        return "tỷ đồng", 1e9
    if "vnd" in q or "vnđ" in q or "dong" in q:
        return "VND", 1.0
    return "VND", 1.0


def source_unit_scale(unit: Any) -> float:
    q = normalized_text(unit)
    if "nghin ty" in q:
        return 1e12
    if "ty" in q:
        return 1e9
    if "trieu" in q:
        return 1e6
    return 1.0


def normalize_row(row: dict, target_scale: float = 1.0) -> dict | None:
    raw_value = parse_number(row.get(RAW_VALUE, row.get("value")))
    if raw_value is None:
        return None
    source_unit = row.get(RAW_UNIT, row.get("source_unit", ""))
    value_vnd = raw_value * source_unit_scale(source_unit)
    result = dict(row)
    result["_raw_value"] = raw_value
    result["_value"] = value_vnd / target_scale
    labels = [
        str(row.get("canonical") or "").strip(),
        str(row.get(RAW_LABEL) or "").strip(),
    ]
    result["_metric"] = next((label for label in labels if is_usable_metric_label(label)), "")
    if not result["_metric"]:
        result["_metric"] = next((label for label in labels if label), "")
    result["_metric_norm"] = normalized_text(result["_metric"])
    result["_metric_alias_norms"] = list(
        dict.fromkeys(
            normalized_text(label)
            for label in (row.get("canonical"), row.get(RAW_LABEL), result["_metric"])
            if str(label or "").strip()
        )
    )
    result["_metric_usable"] = any(
        is_usable_metric_label(label)
        for label in (row.get("canonical"), row.get(RAW_LABEL), result["_metric"])
        if str(label or "").strip()
    )
    result["_company"] = str(row.get("company") or "").strip().upper()
    result["_year"] = int(row.get(RAW_YEAR, row.get("year")))
    consolidated = row.get("is_consolidated")
    if isinstance(consolidated, str):
        consolidated = consolidated.strip().lower() not in {"", "0", "false", "no", "none"}
    result["_scope"] = "consolidated" if bool(consolidated) else "separate"
    result["is_consolidated"] = bool(consolidated)
    result["_source_unit"] = str(source_unit or "VND")
    return result


def build_metric_catalog(rows: Iterable[dict]) -> list[dict]:
    """Create unique raw/canonical labels for question-to-column linking."""
    catalog: dict[str, dict] = {}
    for row in rows:
        canonical_candidates = [
            str(row.get("canonical") or "").strip(),
            str(row.get(RAW_LABEL) or "").strip(),
        ]
        canonical = next((label for label in canonical_candidates if is_usable_metric_label(label)), "")
        for label in (row.get("canonical"), row.get(RAW_LABEL)):
            label = str(label or "").strip()
            key = normalized_text(label)
            if not is_usable_metric_label(label):
                continue
            item = catalog.setdefault(
                key,
                {"label": label, "canonical": canonical or label, "norm": key, "count": 0},
            )
            item["count"] += 1
    return sorted(catalog.values(), key=lambda item: (-len(item["norm"]), -item["count"]))


def match_metrics(question: str, catalog: list[dict], limit: int = 8) -> list[dict]:
    q = normalized_text(question)
    if not q or not catalog:
        return []
    exact: list[dict] = []
    occupied: list[tuple[int, int]] = []
    for item in catalog:
        pos = q.find(item["norm"])
        if pos < 0:
            continue
        span = (pos, pos + len(item["norm"]))
        if any(span[0] >= start and span[1] <= end for start, end in occupied):
            continue
        # Reward items that cover a large portion of the question text.  Many
        # unresolved queries had a long surface form (e.g. ``Tổng tiền trả trước
        # cho người bán ngắn hạn``) which collapsed to a shorter canonical; a
        # coverage bonus surfaces the better-fitting label during ranking.
        coverage = len(item["norm"]) / max(1, len(q))
        bonus = 20.0 if coverage > 0.4 else 0.0
        exact.append({**item, "score": 100.0 + bonus, "position": pos})
        occupied.append(span)
    if exact:
        return sorted(exact, key=lambda item: (item["position"], -item["score"], -len(item["norm"])))[:limit]

    choices = {item["norm"]: item for item in catalog}
    matches = process.extract(q, choices.keys(), scorer=fuzz.token_set_ratio, limit=limit)
    result = []
    for key, score, _ in matches:
        if score < 62:
            continue
        item = choices[key]
        result.append({**item, "score": float(score), "position": 10_000})
    if result and result[0]["score"] >= 70:
        return result

    # OCR and normalization often split/merge a label (for example, a note
    # row can contain ``Chi phí quản lý doanh nghiệp`` without the canonical
    # spelling).  A token-overlap fallback recovers such labels.  We accept
    # a single informative token (>=4 chars) so short phrasings like "Tiền
    # thù lao" still surface during retrieval while we keep the ``năm`` /
    # ``ngắn hạn`` stopwords filtered out.
    query_tokens = {
        token
        for token in q.split()
        if len(token) >= 4 and token not in QUERY_STOPWORDS and not token.isdigit()
    }
    overlap_matches = []
    for item in catalog:
        label_tokens = {token for token in item["norm"].split() if len(token) >= 4}
        overlap = query_tokens & label_tokens
        if len(overlap) < 1:
            continue
        coverage = len(overlap) / max(1, len(label_tokens))
        query_coverage = len(overlap) / max(1, len(query_tokens))
        score = 62.0 + 28.0 * coverage + 10.0 * query_coverage
        overlap_matches.append({**item, "score": score, "position": 10_000})
    overlap_matches.sort(key=lambda item: (-item["score"], -item["count"], len(item["norm"])))
    return overlap_matches[:limit] or result


def extract_entities_v2(
    question: str,
    company_aliases: dict[str, str],
    companies: Iterable[str],
    metric_catalog: list[dict],
) -> dict:
    q_norm = normalized_text(question)
    known = {str(company).upper() for company in companies if company}
    found: list[str] = []
    for ticker in TICKER_RE.findall(str(question).upper()):
        if ticker in known and ticker not in found:
            found.append(ticker)
    for alias, ticker in sorted(company_aliases.items(), key=lambda pair: -len(pair[0])):
        if len(alias) >= 3 and alias in q_norm and ticker in known and ticker not in found:
            found.append(ticker)
    years = [int(match.group(1)) for match in YEAR_RE.finditer(str(question))]
    if len(years) >= 2 and "giai doan" in q_norm:
        years = list(range(min(years), max(years) + 1))
    metric_matches = match_metrics(question, metric_catalog)
    terms = list(dict.fromkeys(item.get("canonical") or item["label"] for item in metric_matches))
    surface_terms = list(dict.fromkeys(item["label"] for item in metric_matches))
    context_terms: list[str] = []
    stopwords = {"cua", "gom", "xet", "trong", "voi", "va", "la", "nam", "den"}
    for match in re.finditer(r"\b(?:nganh|linh vuc)\s+([a-z0-9 ]+)", q_norm):
        words = []
        for word in match.group(1).split():
            if word in stopwords:
                break
            words.append(word)
        if words:
            context_terms.append(" ".join(words))
    context_terms = list(dict.fromkeys(context_terms))
    surface_terms.extend(context_terms)
    unit_name, unit_scale = target_unit(question)
    return {
        "years": list(dict.fromkeys(years)),
        "companies": found,
        "financial_terms": terms,
        "surface_terms": surface_terms,
        "context_terms": context_terms,
        "metric_matches": metric_matches,
        "statement_scope": detect_scope(question),
        "target_unit": unit_name,
        "target_scale": unit_scale,
    }


def infer_operation(question: str, entities: dict) -> str:
    q = normalized_text(question)
    if any(x in q for x in ("bao nhieu cong ty", "bao nhieu ngan hang", "co bao nhieu")):
        return "count"
    if "trung binh" in q or "gia tri binh quan" in q:
        return "mean"
    if any(x in q for x in ("cao nhat", "lon nhat", "thap nhat", "nho nhat")):
        direction = "argmin" if any(x in q for x in ("thap nhat", "nho nhat")) else "argmax"
        if any(x in q for x in ("ty le", "phan tram", "%", "chiem bao nhieu")) and len(entities.get("financial_terms", [])) >= 3:
            return f"{direction}_ratio"
        return direction
    if any(x in q for x in ("ty le", "phan tram", "%", "chiem bao nhieu")) and len(entities.get("financial_terms", [])) >= 2:
        return "ratio"
    if any(x in q for x in ("tong", "cong lai")) and len(entities.get("financial_terms", [])) >= 2:
        return "sum"
    if any(x in q for x in ("chenh lech", "hieu so", "tru ")) and len(entities.get("financial_terms", [])) >= 2:
        return "difference"
    if len(entities.get("years", [])) >= 2 and any(x in q for x in ("tang", "giam", "thay doi", "so voi", "cagr")):
        return "pct_change" if ("phan tram" in q or "%" in q or "cagr" in q) else "year_delta"
    return "lookup"


def py_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _report_year(report_id: Any) -> int | None:
    """Extract the report's reporting year from ``report_id`` (e.g. ``VJC_..._2018_...``)."""
    match = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", str(report_id or ""))
    if not match:
        return None
    year = int(match.group(1))
    return year if 2010 <= year <= 2026 else None


def _row_sign_key(row: dict) -> int:
    """Return 0 for non-negative rows, 1 for negative rows (positive-first ranking)."""
    try:
        value = float(row.get("_raw_value") or 0)
    except (TypeError, ValueError):
        value = 0.0
    return 0 if value >= 0 else 1


def _row_year_match_key(row: dict, years: set[int]) -> int:
    """Return 0 when the row's data year is in the question's year set, else 1."""
    if not years:
        return 1
    return 0 if row.get("_year") in years else 1


def _row_report_year_match_key(row: dict) -> int:
    """Prefer rows whose report year matches the data year (same-year report)."""
    data_year = row.get("_year")
    report_year = _report_year(row.get("report_id"))
    if data_year is None or report_year is None:
        return 1
    return 0 if data_year == report_year else 1


def _row_scope_match_key(row: dict, scope: str) -> int:
    """If the question pins a scope, prefer rows that actually match it."""
    if scope == "any":
        return 0
    return 0 if row.get("_scope") == scope else 1


def dedupe_rows(rows: Iterable[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result = []
    for row in rows:
        key = (
            row.get("report_id"),
            row.get("start_line"),
            row.get("_metric"),
            row.get("_company"),
            row.get("_year"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def select_candidate_rows(index: dict, entities: dict, question: str) -> list[dict]:
    """Filter the full row index without fabricating a fallback row."""
    companies = set(entities.get("companies") or [])
    years = set(entities.get("years") or [])
    terms = [normalized_text(item) for item in entities.get("financial_terms") or []]
    surface_terms = [normalized_text(item) for item in entities.get("surface_terms") or []]
    context_terms = [normalized_text(item) for item in entities.get("context_terms") or []]
    scope = entities.get("statement_scope", "any")
    # Without a company or a metric, a row from the 100-company corpus would
    # be an arbitrary answer rather than grounded retrieval.
    if not companies or not terms:
        return []
    if index.get("by_company_year") is not None:
        pool = []
        by_company_year = index["by_company_year"]
        for company in companies:
            if years:
                for year in years:
                    pool.extend(by_company_year.get((company, year), []))
            else:
                pool.extend(
                    row
                    for (row_company, _), company_rows in by_company_year.items()
                    if row_company == company
                    for row in company_rows
                )
    else:
        pool = index.get("rows", [])
    candidates = []
    for row in pool:
        if companies and row["_company"] not in companies:
            continue
        if years and row["_year"] not in years:
            continue
        if scope != "any" and row["_scope"] != scope:
            continue
        metric_norms = row.get("_metric_alias_norms") or [row["_metric_norm"]]
        if terms:
            canonical_score = max(
                max(
                    100.0 if metric == term else 90.0 if term in metric or metric in term else fuzz.token_set_ratio(metric, term)
                    for metric in metric_norms
                )
                for term in terms
            )
            surface_score = max(
                max(
                    100.0 if metric == term else 90.0 if term in metric or metric in term else fuzz.token_set_ratio(metric, term)
                    for metric in metric_norms
                )
                for term in surface_terms
            ) if surface_terms else 0.0
            score = canonical_score + (20.0 if surface_score >= 95.0 else surface_score / 10.0)
            context_score = max(
                (
                    max(
                        100.0 if context == metric else 90.0 if context in metric or metric in context else fuzz.token_set_ratio(metric, context)
                        for metric in metric_norms
                    )
                    for context in context_terms
                ),
                default=0.0,
            )
            if context_score >= 95.0:
                score = max(score, 120.0 + context_score / 10.0)
            if score < 58 or (not row.get("_metric_usable", False) and context_score < 95.0):
                continue
        else:
            score = 0.0
        item = dict(row)
        item["_match_score"] = float(score)
        candidates.append(item)
    if candidates:
        candidates.sort(
            key=lambda row: (
                -row["_match_score"],
                _row_scope_match_key(row, scope),
                _row_year_match_key(row, years),
                _row_report_year_match_key(row),
                _row_sign_key(row),
                str(row.get("report_id", "")),
                int(row.get("start_line") or 0),
            )
        )
        return dedupe_rows(candidates)

    # A second pass is useful for questions containing a company name but a
    # metric label that was not mapped by the ontology.  It remains grounded:
    # only rows from the requested company/year/scope are returned.
    fallback = []
    q_norm = normalized_text(question)
    for row in pool:
        if companies and row["_company"] not in companies:
            continue
        if years and row["_year"] not in years:
            continue
        if scope != "any" and row["_scope"] != scope:
            continue
        score = fuzz.token_set_ratio(row["_metric_norm"], q_norm)
        if score >= 65:
            item = dict(row)
            item["_match_score"] = float(score)
            fallback.append(item)
    fallback.sort(key=lambda row: -row["_match_score"])
    return dedupe_rows(fallback[:100])


def operation_rows(rows: list[dict], entities: dict) -> list[dict]:
    """Keep a compact, deterministic evidence set for the query compiler."""
    if not rows:
        return []
    terms = [normalized_text(item) for item in entities.get("financial_terms") or []]
    if not terms:
        return rows[:50]
    selected = []
    all_terms = list(dict.fromkeys(terms + [normalized_text(item) for item in entities.get("context_terms") or []]))
    context_terms = {normalized_text(item) for item in entities.get("context_terms") or []}
    for term in all_terms:
        matching = [
            row
            for row in rows
            if row.get("_metric_usable", False) or term in context_terms
            if any(metric == term or term in metric or metric in term for metric in row.get("_metric_alias_norms", [row["_metric_norm"]]))
        ]
        if not matching:
            matching = [
                row
                for row in sorted(
                    (candidate for candidate in rows if candidate.get("_metric_usable", False) or term in context_terms),
                    key=lambda row: -fuzz.token_set_ratio(row["_metric_norm"], term),
                )
                if fuzz.token_set_ratio(row["_metric_norm"], term) >= 75
            ][:1]
        selected.extend(matching[:50])
    return dedupe_rows(selected)[:200]


def to_submission_rows(rows: list[dict], target_scale: float) -> list[dict]:
    result = []
    for row_id, row in enumerate(dedupe_rows(rows)):
        normalized = normalize_row(row, target_scale)
        if normalized is None:
            continue
        result.append(
            {
                "row_id": row_id,
                "metric": normalized["_metric"],
                "canonical": str(row.get("canonical") or ""),
                "company": normalized["_company"],
                "year": normalized["_year"],
                "raw_value": normalized["_raw_value"],
                "source_unit": normalized["_source_unit"],
                "value": normalized["_value"],
                "target_unit": "normalized",
                "report_id": str(row.get("report_id") or ""),
                "start_line": int(row.get("start_line") or 0),
                "is_consolidated": bool(row.get("is_consolidated")),
            }
        )
    return result


def _ordered_labels(question: str, entities: dict, labels: list[str], terms: list[str], operation: str) -> list[str]:
    label_by_norm = {normalized_text(label): label for label in labels}
    ordered = [label_by_norm.get(term) for term in terms if label_by_norm.get(term)]
    ordered += [label for label in labels if label not in ordered]
    if operation not in {"argmax", "argmin", "argmax_ratio", "argmin_ratio"} or len(ordered) < 2:
        return ordered
    marker_positions = [
        normalized_text(question).find(marker)
        for marker in ("cao nhat", "lon nhat", "thap nhat", "nho nhat")
        if normalized_text(question).find(marker) >= 0
    ]
    if not marker_positions:
        return ordered
    marker_position = min(marker_positions)
    matched = [
        item
        for item in entities.get("metric_matches") or []
        if (item.get("canonical") or item.get("label")) in labels and item.get("position", 10_000) < marker_position
    ]
    if not matched:
        return ordered
    selector = label_by_norm.get(normalized_text(matched[-1].get("canonical") or matched[-1]["label"]))
    if selector and selector in ordered:
        return [selector] + [label for label in ordered if label != selector]
    return ordered


def compile_query(question: str, entities: dict, rows: list[dict]) -> tuple[float, str, list[dict], str]:
    """Return answer, executable pandas expression, used rows and operation."""
    if not rows:
        return 0.0, "0.0", [], "unresolved"
    operation = entities.get("operation_override") or infer_operation(question, entities)
    terms = [normalized_text(item) for item in entities.get("financial_terms") or []]
    if operation == "lookup":
        terms = [normalized_text(item) for item in entities.get("context_terms") or []] + terms
    labels = []
    for row in rows:
        if not row.get("_metric_usable", False):
            continue
        if row["_metric"] not in labels:
            labels.append(row["_metric"])
    if not labels:
        labels = [rows[0]["_metric"]]
    ordered_labels = _ordered_labels(question, entities, labels, terms, operation)
    first = ordered_labels[0]
    def exact(label: str) -> list[dict]:
        key = normalized_text(label)
        exact_rows = [row for row in rows if key in row.get("_metric_alias_norms", [row["_metric_norm"]])]
        return exact_rows or [
            row
            for row in rows
            if any(key in metric or metric in key for metric in row.get("_metric_alias_norms", [row["_metric_norm"]]))
        ]

    def pick(candidates: list[dict]) -> dict | None:
        if not candidates:
            return None
        # Prefer a row whose value is non-negative, falling back to the first
        # candidate when every match is negative (rare but possible).
        for row in candidates:
            try:
                if float(row.get("_raw_value") or 0) >= 0:
                    return row
            except (TypeError, ValueError):
                continue
        return candidates[0]

    if operation == "lookup":
        chosen = pick(exact(first)) or (rows[0] if rows else None)
        if chosen is None:
            return 0.0, "0.0", [], "unresolved"
        value = chosen["_value"] / 1.0
        query = f"float(df1.loc[df1[\"row_id\"] == {rows.index(chosen)}, \"value\"].iloc[0])"
        return value, query, [chosen], operation

    if operation in {"sum", "difference", "ratio"} and len(ordered_labels) >= 2:
        a = pick(exact(ordered_labels[0]))
        b = pick(exact(ordered_labels[1]))
        if a is None or b is None:
            return 0.0, "0.0", [], "unresolved"
        av, bv = a["_value"], b["_value"]
        if operation == "sum":
            value, op = av + bv, "+"
        elif operation == "difference":
            value, op = av - bv, "-"
        else:
            value, op = (av / bv * 100 if bv else 0.0), "/"
        ia, ib = rows.index(a), rows.index(b)
        if operation == "ratio":
            query = f"float((df1.loc[df1[\"row_id\"] == {ia}, \"value\"].iloc[0] / df1.loc[df1[\"row_id\"] == {ib}, \"value\"].iloc[0] * 100) if df1.loc[df1[\"row_id\"] == {ib}, \"value\"].iloc[0] != 0 else 0.0)"
        else:
            query = f"float(df1.loc[df1[\"row_id\"] == {ia}, \"value\"].iloc[0] {op} df1.loc[df1[\"row_id\"] == {ib}, \"value\"].iloc[0])"
        return value, query, [a, b], operation

    if operation in {"year_delta", "pct_change"}:
        candidate = exact(first)
        by_year = {}
        for row in candidate:
            by_year.setdefault(row["_year"], row)
        years = sorted(by_year)
        if len(years) >= 2:
            low, high = by_year[years[0]], by_year[years[-1]]
            lv, hv = low["_value"], high["_value"]
            value = (hv - lv) / abs(lv) * 100 if operation == "pct_change" and lv else hv - lv
            il, ih = rows.index(low), rows.index(high)
            if operation == "pct_change":
                query = f"float(((df1.loc[df1[\"row_id\"] == {ih}, \"value\"].iloc[0] - df1.loc[df1[\"row_id\"] == {il}, \"value\"].iloc[0]) / abs(df1.loc[df1[\"row_id\"] == {il}, \"value\"].iloc[0]) * 100) if df1.loc[df1[\"row_id\"] == {il}, \"value\"].iloc[0] != 0 else 0.0)"
            else:
                query = f"float(df1.loc[df1[\"row_id\"] == {ih}, \"value\"].iloc[0] - df1.loc[df1[\"row_id\"] == {il}, \"value\"].iloc[0])"
            return value, query, [low, high], operation

    if operation == "mean":
        chosen = exact(first) or rows
        chosen = [row for row in chosen if float(row.get("_raw_value") or 0) >= 0] or chosen
        ids = [rows.index(row) for row in chosen]
        value = sum(row["_value"] for row in chosen) / len(chosen)
        query = f"float(df1.loc[df1[\"row_id\"].isin({ids}), \"value\"].mean())"
        return value, query, chosen, operation

    if operation in {"argmax", "argmin", "argmax_ratio", "argmin_ratio"} and len(ordered_labels) >= 2:
        selector_label, output_label = ordered_labels[0], ordered_labels[1]
        selector = exact(selector_label)
        output = exact(output_label)
        if selector and output:
            selector_by_key = {(row["_company"], row["_year"]): row for row in selector}
            is_min = operation in {"argmin", "argmin_ratio"}
            key = (min if is_min else max)(selector_by_key, key=lambda item: selector_by_key[item]["_value"])
            outputs = [row for row in output if (row["_company"], row["_year"]) == key]
            if outputs and operation in {"argmax", "argmin"}:
                chosen = outputs[0]
                value = chosen["_value"]
                # Pre-resolve selector/output into a literal lookup.  The
                # original lambda form failed at execution time because the
                # sandbox resolves ``df1`` in the lambda's ``__globals__``
                # which is the merged namespace (see sandbox.py) and the
                # pandas_query parser keeps tripping on the inner ``df1``
                # access.  A direct (company, year, row_id) lookup avoids the
                # lambda entirely and is portable across ``exec``/``eval``.
                sel_row = selector_by_key[key]
                query = (
                    f"float(df1.loc["
                    f"(df1[\"metric\"] == {py_string(output_label)}) & "
                    f"(df1[\"company\"] == {py_string(sel_row['_company'])}) & "
                    f"(df1[\"year\"] == {int(sel_row['_year'])}), "
                    f"\"value\"].iloc[0])"
                )
                return value, query, selector + outputs, operation
            if outputs and operation in {"argmax_ratio", "argmin_ratio"} and len(ordered_labels) >= 3:
                denominator_label = ordered_labels[2]
                denominator = exact(denominator_label)
                denominator_by_key = {(row["_company"], row["_year"]): row for row in denominator}
                denominator_row = denominator_by_key.get(key)
                if denominator_row is not None:
                    numerator_row = outputs[0]
                    denominator_value = denominator_row["_value"]
                    value = numerator_row["_value"] / denominator_value * 100 if denominator_value else 0.0
                    sel_row = selector_by_key[key]
                    query = (
                        f"float((df1.loc["
                        f"(df1[\"metric\"] == {py_string(output_label)}) & "
                        f"(df1[\"company\"] == {py_string(sel_row['_company'])}) & "
                        f"(df1[\"year\"] == {int(sel_row['_year'])}), "
                        f"\"value\"].iloc[0] / "
                        f"df1.loc["
                        f"(df1[\"metric\"] == {py_string(denominator_label)}) & "
                        f"(df1[\"company\"] == {py_string(sel_row['_company'])}) & "
                        f"(df1[\"year\"] == {int(sel_row['_year'])}), "
                        f"\"value\"].iloc[0]) * 100)"
                    )
                    return value, query, selector + outputs + [denominator_row], operation

    if operation == "count":
        chosen = exact(first) or rows
        unique = {(row["_company"], row["_year"]) for row in chosen}
        value = float(len(unique))
        ids = [rows.index(row) for row in chosen]
        query = f"int(df1.loc[df1[\"row_id\"].isin({ids}), \"company\"].nunique())"
        return value, query, chosen, operation

    chosen = pick(exact(first)) or (rows[0] if rows else None)
    if chosen is None:
        return 0.0, "0.0", [], "unresolved"
    value = chosen["_value"]
    query = f"float(df1.loc[df1[\"row_id\"] == {rows.index(chosen)}, \"value\"].iloc[0])"
    return value, query, [chosen], "lookup_fallback"


def submission_rows_from_used(all_rows: list[dict], used_rows: list[dict], target_scale: float) -> list[dict]:
    """Keep all rows needed by a compiled query and assign stable row IDs."""
    used_keys = {
        (row.get("report_id"), row.get("start_line"), row.get("_metric"), row.get("_company"), row.get("_year"))
        for row in used_rows
    }
    compact = [row for row in all_rows if (row.get("report_id"), row.get("start_line"), row.get("_metric"), row.get("_company"), row.get("_year")) in used_keys]
    return to_submission_rows(compact, target_scale)
