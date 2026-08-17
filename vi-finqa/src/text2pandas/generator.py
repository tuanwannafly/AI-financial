"""Template-first pandas generator (no LLM required). LLM hook optional."""
from __future__ import annotations

import re

from .prompts import GENERATION_PROMPT, SYSTEM_PROMPT


def extract_code_block(text: str) -> str:
    m = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()


def template_pandas_code(question: str, entities: dict) -> str:
    cans = entities.get("financial_terms") or []
    cos = entities.get("companies") or []
    years = entities.get("years") or []
    intent = entities.get("intent") or "lookup"
    can0 = cans[0] if cans else None
    co0 = cos[0] if cos else None
    y0 = years[0] if years else None

    ql = question.lower()
    # two tickers with minus in parens: (AAA − ACV)
    import re
    mpair = re.search(r"\(([A-Z]{2,5})\s*[−\-–]\s*([A-Z]{2,5})\)", question)
    if mpair:
        a, b = mpair.group(1), mpair.group(2)
        return (
            f"answer = float(df[df['company']=='{a}']['giá_trị'].iloc[0]) - "
            f"float(df[df['company']=='{b}']['giá_trị'].iloc[0])"
        )
    if intent == "compare_companies" and len(cos) >= 2:
        a, b = cos[0], cos[1]
        return (
            f"answer = float(df[df['company']=='{a}']['giá_trị'].iloc[0]) - "
            f"float(df[df['company']=='{b}']['giá_trị'].iloc[0])"
        )
    # YoY / two years in question
    if len(years) >= 2 and ("tăng" in ql or "giảm" in ql or "so với" in ql or "chênh" in ql):
        ys = sorted(years)
        y1, y2 = ys[0], ys[-1]
        if "phần trăm" in ql or "%" in ql or "cagr" in ql:
            return (
                f"a=float(df[df['năm']=={y2}]['giá_trị'].iloc[0]); "
                f"b=float(df[df['năm']=={y1}]['giá_trị'].iloc[0]); "
                f"answer = (a-b)/abs(b)*100 if b!=0 else None"
            )
        return (
            f"answer = float(df[df['năm']=={y2}]['giá_trị'].iloc[0]) - "
            f"float(df[df['năm']=={y1}]['giá_trị'].iloc[0])"
        )
    if intent in ("compare_years", "trend") and can0 and co0 and len(years) >= 2:
        ys = sorted(years)
        return (
            f"answer = float(df[df['năm']=={ys[-1]}]['giá_trị'].iloc[0]) - "
            f"float(df[df['năm']=={ys[0]}]['giá_trị'].iloc[0])"
        )
    # multi metric sum / diff from wording
    PAIR_SUM = [
        (("nợ ngắn hạn", "nợ dài hạn"), ("Nợ ngắn hạn", "Nợ dài hạn"), "+"),
        (("tiền", "hàng tồn kho"), ("Tiền và tương đương tiền", "Hàng tồn kho"), "+"),
        (("tài sản ngắn hạn", "tài sản dài hạn"), ("Tài sản ngắn hạn", "Tài sản dài hạn"), "+"),
    ]
    PAIR_DIFF = [
        (("doanh thu thuần", "lnst"), ("Doanh thu thuần", "LNST"), "-"),
    ]
    for keys, cans_pair, op in PAIR_SUM + PAIR_DIFF:
        if all(k in ql for k in keys) or ("hiệu số" in ql and op == "-"):
            a, b = cans_pair
            if op == "+":
                return (
                    f"answer = float(df[df['canonical']=='{a}']['giá_trị'].iloc[0]) + "
                    f"float(df[df['canonical']=='{b}']['giá_trị'].iloc[0])"
                )
            return (
                f"answer = float(df[df['canonical']=='{a}']['giá_trị'].iloc[0]) - "
                f"float(df[df['canonical']=='{b}']['giá_trị'].iloc[0])"
            )
    if intent == "calc_ratio" and len(cans) >= 2:
        return (
            f"answer = float(df[df['canonical']=='{cans[0]}']['giá_trị'].iloc[0]) / "
            f"float(df[df['canonical']=='{cans[1]}']['giá_trị'].iloc[0]) * 100"
        )
    if can0 and co0 and y0:
        return (
            f"answer = float(df[(df['canonical']=='{can0}') & (df['năm']=={y0}) "
            f"& (df['company']=='{co0}')]['giá_trị'].iloc[0])"
        )
    if can0:
        return f"answer = float(df[df['canonical']=='{can0}']['giá_trị'].iloc[0])"
    return "answer = float(df['giá_trị'].iloc[0])"


def generate_pandas_code(question: str, table_desc: str, few_shot: str, llm_call_fn=None, entities: dict | None = None) -> str:
    if llm_call_fn is None:
        return template_pandas_code(question, entities or {})
    prompt = GENERATION_PROMPT.format(
        few_shot_examples=few_shot, table_desc=table_desc, question=question
    )
    raw = llm_call_fn(SYSTEM_PROMPT + "\n\n" + prompt)
    return extract_code_block(raw)
