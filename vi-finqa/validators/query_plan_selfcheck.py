"""Small regression checks for the v2 grounding/query compiler."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from src.finalize.query_plan import (
    build_metric_catalog,
    compile_query,
    extract_entities_v2,
    normalize_row,
    operation_rows,
    select_candidate_rows,
)
from src.synthetic.sandbox import execute_inline_code


def _row(metric, value, canonical, company="VJC", year=2018, consolidated=False):
    return {
        "chỉ_tiêu": metric,
        "năm": year,
        "giá_trị": value,
        "đơn_vị": "Đơn vị: VND",
        "canonical": canonical,
        "company": company,
        "is_consolidated": consolidated,
        "report_id": f"{company}_financial_statements_{year}_separate_extracted",
        "start_line": 100,
    }


def main() -> int:
    raw_rows = [
        _row("Lãi tiền gửi", 3_648_963_007_451, "Doanh thu tài chính", consolidated=False),
        _row("Lãi tiền gửi", 3_640_399_241_738, "Doanh thu tài chính", consolidated=True),
    ]
    normalized = [normalize_row(row) for row in raw_rows]
    index = {"rows": normalized, "metrics": build_metric_catalog(normalized), "companies": ["VJC"]}
    entities = extract_entities_v2(
        "Lãi tiền gửi năm 2018 của công ty mẹ CTCP Hàng không Vietjet (VJC) là bao nhiêu triệu đồng?",
        {"vjc": "VJC", "ctcp hang khong vietjet": "VJC"},
        ["VJC"],
        index["metrics"],
    )
    assert entities["companies"] == ["VJC"]
    assert entities["statement_scope"] == "separate"
    assert entities["target_scale"] == 1e6
    candidates = select_candidate_rows(index, entities, "")
    planned = operation_rows(candidates, entities)
    question_rows = [normalize_row(row, entities["target_scale"]) for row in planned]
    answer, query, used, operation = compile_query("lookup", entities, question_rows)
    assert operation == "lookup"
    assert answer == 3_648_963.007451
    with tempfile.TemporaryDirectory() as directory:
        csv_path = Path(directory) / "evidence.csv"
        pd.DataFrame(
            [
                {"row_id": i, "metric": row["_metric"], "company": row["_company"], "year": row["_year"], "value": row["_value"]}
                for i, row in enumerate(question_rows)
            ]
        ).to_csv(csv_path, index=False)
        assert execute_inline_code(query, str(csv_path)) == answer
    print("query_plan_selfcheck: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
