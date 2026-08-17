"""Build a grounded official ViFinQA submission.

The old packer was a 506-question prototype.  It selected the first row of a
candidate CSV, ignored statement scope and units, and used ``unknown|0`` for
unmapped questions.  This version consumes the complete question file and
compiles a deterministic query plan over grounded evidence rows.
"""
from __future__ import annotations

import json
import math
import re
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

from ..finalize.query_plan import (
    RAW_LABEL,
    RAW_UNIT,
    RAW_VALUE,
    RAW_YEAR,
    build_metric_catalog,
    compile_query,
    extract_entities_v2,
    infer_operation,
    load_company_aliases,
    normalize_row,
    normalized_text,
    operation_rows,
    select_candidate_rows,
    to_submission_rows,
)
from ..schema.longify import _cell_unit, _value, detect_year_columns
from ..synthetic.sandbox import execute_inline_code


def load_official(path: str = "data/raw/questions/questions.jsonl", n: int | None = None) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if n is not None and len(rows) >= n:
                break
    return rows


def report_id_official(stem: str) -> str:
    """BTC report ID: final path component without ``.txt``/``_extracted``."""
    value = str(stem or "").replace("\\", "/").split("/")[-1]
    if value.endswith(".txt"):
        value = value[:-4]
    if value.endswith("_extracted"):
        value = value[: -len("_extracted")]
    return value or "unknown"


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _metadata_year_columns(rows: list[list[str]], record_year: int | None) -> dict[int, int]:
    """Detect both standard headers and compact headers such as ``2018VND``."""
    mapping = dict(detect_year_columns(rows, record_year))
    bare_year = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
    for header in rows[:6]:
        header_years: list[tuple[int, int]] = []
        for index, cell in enumerate(header):
            match = bare_year.search(str(cell or ""))
            if match:
                year = int(match.group(1))
                if 2010 <= year <= 2026:
                    header_years.append((index, year))
        # Some OCR tables place the first value-column date in cell 0 and
        # shift the actual row labels to the next cell.
        if header_years and header_years[0][0] == 0:
            for offset, (_, year) in enumerate(header_years):
                mapping[1 + offset] = year
        for index, cell in enumerate(header):
            if index == 0 or index in mapping:
                continue
            match = bare_year.search(str(cell or ""))
            if match:
                year = int(match.group(1))
                if 2010 <= year <= 2026:
                    mapping[index] = year
    return mapping


def _metadata_long_rows(
    metadata_path: str = "data/extracted/metadata.jsonl",
    canonical_by_norm: dict[str, str] | None = None,
):
    """Yield numeric rows from all extracted table types, including notes.

    The original longifier intentionally restricted itself to the three main
    statements.  The official questions also target note tables, so the
    official pack uses the already extracted metadata as an additional source.
    """
    path = Path(metadata_path)
    if not path.exists():
        return
    canonical_by_norm = canonical_by_norm or {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            rows = record.get("rows") or []
            record_year = _as_int(record.get("year"))
            year_columns = _metadata_year_columns(rows, record_year)
            if not year_columns:
                continue
            unit = record.get("unit")
            for header in rows[:6]:
                for cell in header:
                    unit = unit or _cell_unit(str(cell or ""))
                    if unit:
                        break
                if unit:
                    break
            start_index = 0
            for index, header in enumerate(rows[:6]):
                if any(column in year_columns for column in range(1, len(header))):
                    start_index = index + 1
                    break
            for row in rows[start_index:]:
                if not row or not str(row[0] or "").strip():
                    continue
                label = str(row[0]).strip()
                for column, year in sorted(year_columns.items()):
                    if column >= len(row):
                        continue
                    value = _value(str(row[column] or ""))
                    if value is None:
                        continue
                    item = {
                        "chỉ_tiêu": label,
                        "năm": year,
                        "giá_trị": value,
                        "đơn_vị": unit,
                        "report_id": record.get("report_id"),
                        "start_line": record.get("start_line"),
                        "table_type": record.get("table_type"),
                        "company": record.get("company"),
                        "is_consolidated": record.get("is_consolidated"),
                    }
                    canonical = canonical_by_norm.get(normalized_text(label))
                    if canonical:
                        item["canonical"] = canonical
                    yield item


def _load_canonical_map(path: str = "data/processed/normalized_terms.jsonl") -> dict[str, str]:
    mapping: dict[str, str] = {}
    source = Path(path)
    if not source.exists():
        return mapping
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            canonical = str(row.get("canonical") or "").strip()
            if canonical:
                for label in (row.get("raw"), row.get("clean")):
                    key = normalized_text(label)
                    if key:
                        mapping[key] = canonical
    return mapping


def build_long_index(
    path: str = "data/processed/long_format_mapped.jsonl",
    metadata_path: str = "data/extracted/metadata.jsonl",
) -> dict:
    """Load every numeric row and build a full metric catalog.

    Values in the index use VND as the internal base unit.  Per-question unit
    conversion happens after candidate selection so ratios and comparisons use
    a consistent unit.
    """
    rows: list[dict] = []
    by_key: dict[tuple, list[dict]] = {}
    by_company_year: dict[tuple[str, int], list[dict]] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            company = str(raw.get("company") or "").strip().upper()
            year = _as_int(raw.get(RAW_YEAR, raw.get("year")))
            if not company or year is None:
                continue
            raw["company"] = company
            raw[RAW_YEAR] = year
            normalized = normalize_row(raw, target_scale=1.0)
            if normalized is None or not normalized.get("_metric"):
                continue
            rows.append(normalized)
            key = (company, year, normalized["_metric"])
            by_key.setdefault(key, []).append(normalized)
            by_company_year.setdefault((company, year), []).append(normalized)

    canonical_by_norm = _load_canonical_map()
    for raw in _metadata_long_rows(metadata_path, canonical_by_norm):
        company = str(raw.get("company") or "").strip().upper()
        year = _as_int(raw.get(RAW_YEAR, raw.get("year")))
        if not company or year is None:
            continue
        raw["company"] = company
        raw[RAW_YEAR] = year
        normalized = normalize_row(raw, target_scale=1.0)
        if normalized is None or not normalized.get("_metric"):
            continue
        rows.append(normalized)
        key = (company, year, normalized["_metric"])
        by_key.setdefault(key, []).append(normalized)
        by_company_year.setdefault((company, year), []).append(normalized)

    for candidates in by_key.values():
        candidates.sort(key=lambda row: (-row.get("_match_score", 0), str(row.get("report_id", "")), int(row.get("start_line") or 0)))
    return {
        "rows": rows,
        "by_key": by_key,
        "by_company_year": by_company_year,
        "metrics": build_metric_catalog(rows),
        "companies": sorted({row["_company"] for row in rows}),
    }


def rows_for_entities(index: dict, entities: dict, question: str = "") -> list[dict]:
    """Compatibility wrapper used by earlier scripts."""
    if "rows" in index:
        return select_candidate_rows(index, entities, question)
    # Accept the old ``{(company, year, canonical): rows}`` shape as well.
    output = []
    for (company, year, _), rows in index.items():
        if entities.get("companies") and company not in entities["companies"]:
            continue
        if entities.get("years") and year not in entities["years"]:
            continue
        output.extend(rows)
    return output


def to_eval_query(code: str) -> str:
    """Keep the old public helper, but never replace a valid query by row 0."""
    query = str(code or "").strip()
    query = query.replace("answer = ", "", 1).replace("answer=", "", 1).strip()
    return query or "0.0"


def _used_table_keys(rows: list[dict]) -> list[str]:
    result = []
    seen = set()
    for row in rows:
        report = report_id_official(str(row.get("report_id") or ""))
        line = int(row.get("start_line") or 0)
        if report == "unknown":
            continue
        key = f"{report}|{line}"
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def _used_docs(rows: list[dict]) -> list[str]:
    result = []
    seen = set()
    for row in rows:
        report = report_id_official(str(row.get("report_id") or ""))
        if report != "unknown" and report not in seen:
            seen.add(report)
            result.append(report)
    return result


def _fallback_csv(path: Path) -> None:
    pd.DataFrame(
        [{
            "row_id": 0,
            "metric": "",
            "canonical": "",
            "company": "",
            "year": 0,
            "raw_value": 0.0,
            "source_unit": "",
            "value": 0.0,
            "target_unit": "normalized",
            "report_id": "",
            "start_line": 0,
            "is_consolidated": False,
        }]
    ).to_csv(path, index=False, encoding="utf-8")


def _finite_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _execute(query: str, csv_path: Path) -> tuple[bool, float | None, str | None]:
    try:
        value = execute_inline_code(query, str(csv_path))
        if not _finite_number(value):
            return False, None, "query returned a non-finite value"
        return True, float(value), None
    except Exception as exc:  # pragma: no cover - exact pandas error depends on input rows
        return False, None, str(exc)


def pack_official(
    n: int | None = None,
    out_zip: str = "submissions/submission.zip",
    questions_path: str = "data/raw/questions/questions.jsonl",
    long_path: str = "data/processed/long_format_mapped.jsonl",
    use_llm: bool = False,
    llm_model: str | None = None,
) -> dict:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from validators.submission_validator import validate_submission

    questions = load_official(questions_path, n=n)
    index = build_long_index(long_path)
    aliases = load_company_aliases()
    companies = index["companies"]
    planner = None
    llm_error = None
    if use_llm:
        try:
            from ..text2pandas.local_planner import LocalQueryPlanner

            planner = LocalQueryPlanner(model_name=llm_model)
        except Exception as exc:  # pragma: no cover - optional path
            llm_error = str(exc)

    # A staging directory is intentionally separate from old _pack artifacts;
    # rerunning the packer never deletes unrelated user files.
    staging = Path(out_zip).parent / "_pack_v2"
    data_dir = staging / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    audit = {
        "questions": len(questions),
        "resolved": 0,
        "unresolved": 0,
        "execution_ok": 0,
        "unknown_company": 0,
        "unknown_metric": 0,
        "operations": Counter(),
        "scopes": Counter(),
        "unresolved_ids": [],
        "execution_errors": [],
        "llm_enabled": bool(use_llm),
        "llm_error": llm_error,
    }

    for question in questions:
        qid = int(question["id"])
        text = str(question.get("question") or "")
        entities = extract_entities_v2(text, aliases, companies, index["metrics"])
        if planner and entities.get("financial_terms"):
            try:
                decision = planner.plan(text, entities["financial_terms"])
                if decision:
                    entities["operation_override"] = decision["operation"]
                    if decision.get("metric_labels"):
                        entities["financial_terms"] = decision["metric_labels"]
            except Exception as exc:  # pragma: no cover - model/runtime dependent
                llm_error = str(exc)
                audit["llm_error"] = llm_error
        entities["operation"] = entities.get("operation_override") or infer_operation(text, entities)
        audit["operations"][entities["operation"]] += 1
        audit["scopes"][entities["statement_scope"]] += 1
        if not entities["companies"]:
            audit["unknown_company"] += 1
        if not entities["financial_terms"]:
            audit["unknown_metric"] += 1

        candidates = rows_for_entities(index, entities, text)
        planning_rows = operation_rows(candidates, entities)
        target_scale = float(entities.get("target_scale") or 1.0)
        question_rows = []
        for row in planning_rows:
            normalized = normalize_row(row, target_scale=target_scale)
            if normalized is not None:
                question_rows.append(normalized)

        csv_name = f"q_{qid}.csv"
        csv_rel = f"data/{csv_name}"
        csv_path = data_dir / csv_name
        answer, query, used_rows, operation = compile_query(text, entities, question_rows)
        csv_rows = to_submission_rows(question_rows, target_scale=1.0)

        # compile_query uses row indexes from question_rows.  The output rows
        # must therefore preserve the exact same order and values; it is safer
        # to write the already-normalized values directly here.
        if question_rows:
            csv_rows = []
            for row_id, row in enumerate(question_rows):
                csv_rows.append(
                    {
                        "row_id": row_id,
                        "metric": row["_metric"],
                        "canonical": str(row.get("canonical") or ""),
                        "company": row["_company"],
                        "year": row["_year"],
                        "raw_value": row["_raw_value"],
                        "source_unit": row["_source_unit"],
                        "value": row["_value"],
                        "target_unit": entities.get("target_unit", "VND"),
                        "report_id": str(row.get("report_id") or ""),
                        "start_line": int(row.get("start_line") or 0),
                        "is_consolidated": bool(row.get("is_consolidated")),
                    }
                )
            pd.DataFrame(csv_rows).to_csv(csv_path, index=False, encoding="utf-8")
        else:
            _fallback_csv(csv_path)
            audit["unresolved"] += 1
            audit["unresolved_ids"].append(qid)
            answer, query, used_rows, operation = 0.0, "0.0", [], "unresolved"

        executed, executed_value, error = _execute(query, csv_path)
        if executed:
            audit["execution_ok"] += 1
            answer = executed_value
        else:
            audit["execution_errors"].append({"id": qid, "error": error, "query": query})
            # Do not silently replace an invalid query with the first CSV row.
            answer = 0.0
            query = "0.0"

        if used_rows:
            audit["resolved"] += 1
        docs = _used_docs(used_rows)
        tables = _used_table_keys(used_rows)
        entries.append(
            {
                "id": qid,
                "question": text,
                "answer": float(answer),
                "relevant_docs": docs,
                "relevant_tables": tables,
                "evidence": [{"variable": "df1", "csv_path": csv_rel}],
                "pandas_query": query,
            }
        )

    audit["operations"] = dict(audit["operations"])
    audit["scopes"] = dict(audit["scopes"])
    audit["all_ids_unique"] = len({entry["id"] for entry in entries}) == len(entries)
    audit["expected_ids"] = list(range(1, len(entries) + 1))
    audit["ids_are_sequential"] = [entry["id"] for entry in entries] == audit["expected_ids"]

    json_path = staging / "submission.json"
    json_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_path = Path("stats/official_pack_audit.json")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    output = Path(out_zip)
    output.parent.mkdir(parents=True, exist_ok=True)
    needed_csv_names = {f"q_{entry['id']}.csv" for entry in entries}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(json_path, arcname="submission.json")
        for csv_path in sorted(data_dir.glob("*.csv")):
            if csv_path.name in needed_csv_names:
                archive.write(csv_path, arcname=f"data/{csv_path.name}")

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    schema_ok = (
        "submission.json" in names
        and all(name == "submission.json" or name.startswith("data/") for name in names)
        and len(entries) == len(questions)
        and audit["all_ids_unique"]
        and all(entry["evidence"][0]["csv_path"] in names for entry in entries)
    )
    try:
        validation = validate_submission(str(output), expected_n=len(questions))
    except Exception as exc:  # pragma: no cover
        validation = {"pass": False, "errors": [str(exc)]}

    return {
        "n": len(entries),
        "n_exec_ok": audit["execution_ok"],
        "n_resolved": audit["resolved"],
        "n_unresolved": audit["unresolved"],
        "id_first": entries[0]["id"] if entries else None,
        "id_last": entries[-1]["id"] if entries else None,
        "zip": str(output),
        "audit": str(audit_path),
        "zip_root_files": names[:6],
        "schema_ok": schema_ok,
        "local_validator": validation,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=None, help="optional question limit; default is all questions")
    parser.add_argument("--out", default="submissions/submission.zip")
    parser.add_argument("--questions", default="data/raw/questions/questions.jsonl")
    parser.add_argument("--llm", action="store_true", help="use optional local open-weight planner")
    parser.add_argument("--llm-model", default=None)
    args = parser.parse_args()
    print(json.dumps(pack_official(n=args.n, out_zip=args.out, questions_path=args.questions, use_llm=args.llm, llm_model=args.llm_model), ensure_ascii=False, indent=2))
