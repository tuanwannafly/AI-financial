"""Week 3/4 E2E: retrieve + template (or LLM) pandas + optional repair."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from validators.local_scorer import answer_match, table_retrieval_score

from ..retrieval.indexer import load_bundle
from ..retrieval.query_understanding import classify_intent, expand_query, extract_entities
from ..retrieval.retriever import HybridRetriever, RetrieverConfig
from ..schema.normalize import build_alias_index, load_ontology
from ..synthetic.sandbox import execute_inline_code
from ..text2pandas.generator import generate_pandas_code
from ..text2pandas.repair import sanity_check, self_repair
from ..text2pandas.serialize import serialize_markdown_table, serialize_structured_text


def load_retriever(bundle_path: str = "data/retrieval_index/bm25_metric.pkl", top_k: int = 20):
    bundle = load_bundle(bundle_path)
    cfg = RetrieverConfig(top_k_bm25=80, top_k_final=top_k)
    retriever = HybridRetriever(bundle["documents"], bundle["doc_meta"], bundle["bm25"], config=cfg)
    companies = sorted({m.get("company") for m in bundle["doc_meta"] if m.get("company")})
    return retriever, bundle, companies


def run_e2e(
    question: str,
    retriever,
    ontology,
    alias_index,
    company_list,
    csv_path: str | None = None,
    use_repair: bool = True,
    serializer_name: str = "markdown",
    extra_entities: dict | None = None,
) -> dict:
    entities = extract_entities(question, alias_index, company_list)
    entities["intent"] = classify_intent(question, entities)
    if extra_entities:
        entities.update(extra_entities)
    expanded = expand_query(question, entities, ontology)
    filters = {"company": entities["companies"][0]} if entities["companies"] else None
    tables = retriever.retrieve(expanded, filters=filters)
    if not tables:
        return {"status": "no_retrieval", "retrieved": [], "result": {"success": False}, "entities": entities}

    t0 = tables[0]
    path = csv_path or t0.get("csv_path")
    csv_rows = []
    csv_columns = ["chỉ_tiêu", "canonical", "năm", "giá_trị"]
    if path and Path(path).exists():
        try:
            evidence_df = pd.read_csv(path)
            csv_columns = [str(column) for column in evidence_df.columns]
            csv_rows = evidence_df.head(40).fillna("").to_dict(orient="records")
        except Exception:
            csv_rows = []
    table_for_ser = {
        "company": t0.get("company"),
        "year": t0.get("year"),
        "table_type": t0.get("table_type"),
        "unit": t0.get("unit"),
        "columns": csv_columns,
        "rows": csv_rows,
    }
    if serializer_name == "structured":
        table_desc = serialize_structured_text(table_for_ser, alias_index)
    else:
        table_desc = serialize_markdown_table(table_for_ser)

    code = generate_pandas_code(question, table_desc, "", llm_call_fn=None, entities=entities)
    if use_repair and path:
        repair_result = self_repair(question, table_desc, code, path, llm_call_fn=None, entities=entities)
    elif path:
        try:
            val = execute_inline_code(code, path)
            ok = sanity_check(val)
            repair_result = {"success": ok, "code": code, "value": val if ok else None, "attempts": [{"attempt": 0, "status": "ok" if ok else "bad"}]}
        except Exception as e:
            repair_result = {"success": False, "code": code, "value": None, "attempts": [{"status": "error", "err": str(e)}]}
    else:
        repair_result = {"success": False, "code": code, "value": None, "attempts": []}

    return {
        "status": "done",
        "retrieved": tables,
        "result": repair_result,
        "entities": entities,
        "query": code,
    }


def classify_error(gold_item: dict, e2e_result: dict) -> str:
    gold_tables = set(gold_item.get("relevant_tables") or [])
    retrieved_keys = {f"{t.get('report_id')}|{t.get('start_line')}" for t in e2e_result.get("retrieved") or []}
    if not (gold_tables & retrieved_keys):
        return "retrieval_miss"
    res = e2e_result.get("result") or {}
    if not res.get("success"):
        return "execution_fail_unrepaired"
    pred, gold_answer = res.get("value"), gold_item.get("answer")
    try:
        if answer_match(float(pred), float(gold_answer)):
            return "ok"
        if gold_answer and float(gold_answer) != 0:
            ratio = abs(float(pred) / float(gold_answer))
            if any(abs(ratio - m) < 0.05 for m in (1000, 0.001, 1_000_000, 1e-6, 1e9, 1e-9)):
                return "unit_mismatch"
    except Exception:
        return "generation_wrong_logic"
    return "generation_wrong_logic"


def evaluate_e2e(gold_set, retriever, ontology, alias, companies, use_repair=True, top_k=20) -> dict:
    breakdown = {
        "ok": 0,
        "retrieval_miss": 0,
        "execution_fail_unrepaired": 0,
        "unit_mismatch": 0,
        "generation_wrong_logic": 0,
    }
    f2s, exec_hits, ans_hits = [], 0, 0
    details = []
    for g in gold_set:
        result = run_e2e(
            g["question"],
            retriever,
            ontology,
            alias,
            companies,
            csv_path=g.get("csv_path") or g.get("evidence_csv"),
            use_repair=use_repair,
        )
        cat = classify_error(g, result) if result.get("status") == "done" else "retrieval_miss"
        breakdown[cat] += 1
        pred_keys = {f"{t.get('report_id')}|{t.get('start_line')}" for t in result.get("retrieved") or []}
        sc = table_retrieval_score(pred_keys, set(g.get("relevant_tables") or []))
        f2s.append(sc["f2"])
        if result.get("result", {}).get("success"):
            exec_hits += 1
            try:
                if answer_match(float(result["result"]["value"]), float(g["answer"])):
                    ans_hits += 1
            except Exception:
                pass
        details.append({"question_id": g.get("question_id"), "category": g.get("category"), "error_category": cat})
    n = len(gold_set) or 1
    return {
        "breakdown": breakdown,
        "rates": {k: v / n for k, v in breakdown.items()},
        "f2": sum(f2s) / len(f2s) if f2s else 0,
        "exec_acc": exec_hits / n,
        "answer_acc": ans_hits / n,
        "n": n,
        "details": details,
    }


def run_and_save(out_path: str = "stats/e2e_eval.json", use_repair: bool = True) -> dict:
    gold = json.loads(Path("data/gold/gold_set.json").read_text(encoding="utf-8"))
    retriever, _, companies = load_retriever()
    ontology = load_ontology()
    alias = build_alias_index(ontology)
    ev = evaluate_e2e(gold, retriever, ontology, alias, companies, use_repair=use_repair)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
    return {k: ev[k] for k in ("breakdown", "rates", "f2", "exec_acc", "answer_acc", "n")}


if __name__ == "__main__":
    print(json.dumps(run_and_save(), ensure_ascii=False, indent=2))
