from __future__ import annotations

import re

YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

INTENT_KEYWORDS = {
    "compare_years": [
        "so sánh", "tăng trưởng", "so với năm", "biến động", "tăng bao nhiêu",
        "cagr", "sang năm", "tăng/giảm", "tăng giảm", "chênh lệch",
    ],
    "calc_ratio": ["tỷ lệ", "cơ cấu", "phần trăm", "%", "chiếm bao nhiêu"],
    "financial_index": ["roe", "roa", "eps", "biên lợi nhuận", "vòng quay", "biên lnst"],
    "trend": ["xu hướng", "qua các năm", "cagr", "giai đoạn"],
    "sum_two": ["tổng nợ", "tổng ", "tiền +", "+ hàng tồn"],
    "diff_two": ["hiệu số", "và lnst", "trừ lnst"],
}


def extract_entities(query: str, ontology_alias_index: dict, company_list: list[str]) -> dict:
    from ..schema.normalize import key_of

    years = [int(m.group(1)) for m in YEAR_RE.finditer(query)]
    ql = query.lower()
    qk = key_of(query)
    companies = [c for c in company_list if c and c.lower() in ql]
    terms = []
    # longer aliases first
    items = sorted(ontology_alias_index.items(), key=lambda x: -len(x[0] or ""))
    for alias, canon in items:
        if not alias:
            continue
        if alias in ql or alias in qk or key_of(alias) in qk:
            terms.append(canon)
    return {"years": years, "companies": companies, "financial_terms": list(dict.fromkeys(terms))}


def classify_intent(query: str, entities: dict) -> str:
    q = query.lower()
    if len(entities.get("companies") or []) >= 2:
        return "compare_companies"
    for intent, kws in INTENT_KEYWORDS.items():
        if kws and any(kw in q for kw in kws):
            return intent
    return "lookup"


def expand_query(query: str, entities: dict, ontology: dict) -> str:
    extra = []
    for term in entities.get("financial_terms") or []:
        extra.extend((ontology.get(term) or {}).get("aliases", [])[:3])
    return (query + " " + " ".join(extra)).strip()
