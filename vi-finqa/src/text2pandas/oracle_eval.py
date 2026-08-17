from __future__ import annotations

import json
from pathlib import Path

from ..retrieval.query_understanding import classify_intent, extract_entities
from ..schema.normalize import build_alias_index, load_ontology
from ..synthetic.sandbox import execute_inline_code
from ..text2pandas.generator import generate_pandas_code
from ..text2pandas.repair import sanity_check, self_repair
from ..text2pandas.serialize import (
    serialize_compact_json,
    serialize_markdown_table,
    serialize_relevant_columns_only,
    serialize_structured_text,
)

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validators.local_scorer import answer_match


def _table_from_csv(g: dict) -> dict:
    import pandas as pd

    p = g.get("csv_path") or g.get("evidence_csv")
    df = pd.read_csv(p) if p and Path(p).exists() else None
    rows = df.to_dict("records") if df is not None else []
    return {
        "company": (g.get("meta") or {}).get("company"),
        "year": (g.get("meta") or {}).get("year"),
        "columns": list(df.columns) if df is not None else [],
        "rows": [[r.get("chỉ_tiêu"), r.get("canonical"), r.get("năm"), r.get("giá_trị")] for r in rows[:15]],
        "csv_path": p,
        "unit": g.get("unit"),
    }


def run_oracle_eval(gold_set, serializer_name="markdown", use_repair=False) -> dict:
    ontology = load_ontology()
    alias = build_alias_index(ontology)
    companies = []
    results = []
    for g in gold_set:
        table = _table_from_csv(g)
        if serializer_name == "structured":
            desc = serialize_structured_text(table, alias)
        elif serializer_name == "json":
            desc = serialize_compact_json(table)
        elif serializer_name == "relevant":
            ents = extract_entities(g["question"], alias, companies)
            desc = serialize_relevant_columns_only(table, ents.get("financial_terms") or [])
        else:
            desc = serialize_markdown_table(table)
        ents = extract_entities(g["question"], alias, companies)
        ents["intent"] = classify_intent(g["question"], ents)
        # inject gold meta company if QU missed ticker
        meta = g.get("meta") or {}
        if meta.get("company") and meta["company"] not in (ents.get("companies") or []):
            ents["companies"] = [meta["company"]] + (ents.get("companies") or [])
        if meta.get("year") and meta["year"] not in (ents.get("years") or []):
            ents["years"] = [int(meta["year"])] + (ents.get("years") or [])
        if meta.get("canonical") and meta["canonical"] not in (ents.get("financial_terms") or []):
            ents["financial_terms"] = [meta["canonical"]] + (ents.get("financial_terms") or [])
        code = generate_pandas_code(g["question"], desc, "", None, ents)
        csv_path = table["csv_path"]
        if use_repair:
            rr = self_repair(g["question"], desc, code, csv_path, None, entities=ents)
            status = "ok" if rr["success"] else "error"
            value = rr.get("value")
            code = rr.get("code", code)
        else:
            try:
                value = execute_inline_code(code, csv_path)
                status = "ok" if sanity_check(value) else "error"
            except Exception as e:
                status, value = "error", str(e)
        first_try_ok = False
        try:
            first_try_ok = status == "ok" and value is not None and answer_match(float(value), float(g["answer"]))
        except Exception:
            first_try_ok = False
        results.append(
            {
                "question_id": g["question_id"],
                "status": status,
                "first_try_ok": first_try_ok,
                "code": code,
                "value": value if not isinstance(value, str) or status == "ok" else None,
                "question": g["question"],
            }
        )
    n = len(results) or 1
    return {
        "exec_rate": sum(r["status"] == "ok" for r in results) / n,
        "first_try_answer_acc": sum(r["first_try_ok"] for r in results) / n,
        "fails": [r for r in results if not r["first_try_ok"]],
        "n": n,
        "serializer": serializer_name,
    }


def compare_serializers(gold_set) -> dict:
    names = ["markdown", "structured", "json", "relevant"]
    scored = {}
    for name in names:
        ev = run_oracle_eval(gold_set, serializer_name=name, use_repair=False)
        scored[name] = ev["first_try_answer_acc"]
    best = max(scored, key=scored.get)
    return {"scores": scored, "best": best}


if __name__ == "__main__":
    gold = json.loads(Path("data/gold/gold_set.json").read_text(encoding="utf-8"))
    cmp = compare_serializers(gold)
    best_full = run_oracle_eval(gold, serializer_name=cmp["best"], use_repair=False)
    repaired = run_oracle_eval(gold, serializer_name=cmp["best"], use_repair=True)
    out = {
        "compare": cmp,
        "oracle_best": {k: best_full[k] for k in ("exec_rate", "first_try_answer_acc", "n", "serializer")},
        "oracle_repaired": {k: repaired[k] for k in ("exec_rate", "first_try_answer_acc", "n")},
        "repair_delta_exec_points": (repaired["exec_rate"] - best_full["exec_rate"]) * 100,
    }
    Path("stats/oracle_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    logic = [f for f in best_full["fails"] if f["status"] == "ok"]
    Path("data/text2pandas").mkdir(parents=True, exist_ok=True)
    Path("data/text2pandas/logic_fail_review_batch.json").write_text(
        json.dumps(logic[:80], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
