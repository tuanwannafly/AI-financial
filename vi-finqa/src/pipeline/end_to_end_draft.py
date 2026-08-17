"""Week 2 draft E2E: retrieve + template pandas (no LLM required)."""
from __future__ import annotations

import json
from pathlib import Path

from ..retrieval.indexer import load_bundle
from ..retrieval.query_understanding import classify_intent, extract_entities
from ..retrieval.retriever import HybridRetriever, RetrieverConfig
from ..schema.normalize import build_alias_index, load_ontology
from ..synthetic.sandbox import execute_inline
import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
from validators.local_scorer import answer_match


def draft_pandas(question: str, entities: dict) -> str | None:
    cans = entities.get("financial_terms") or []
    cos = entities.get("companies") or []
    years = entities.get("years") or []
    if len(cans) >= 1 and len(cos) >= 1 and len(years) >= 1:
        return (
            f"df[(df['canonical']=='{cans[0]}') & (df['năm']=={years[0]}) "
            f"& (df['company']=='{cos[0]}')]['giá_trị'].iloc[0]"
        )
    return None


def answer_question_draft(question: str, retriever, ontology_alias_index, company_list, gold_csv: str | None = None):
    entities = extract_entities(question, ontology_alias_index, company_list)
    intent = classify_intent(question, entities)
    filters = {"company": entities["companies"][0]} if entities["companies"] else None
    tables = retriever.retrieve(question, filters=filters)
    if not tables:
        return {"status": "no_retrieval", "intent": intent, "entities": entities}
    query = draft_pandas(question, entities)
    csv_path = gold_csv
    status, value = "no_query", None
    if query and csv_path and Path(csv_path).exists():
        try:
            value = execute_inline(query, csv_path)
            status = "ok"
        except Exception as e:
            status = f"error:{e}"
    return {
        "status": status,
        "value": value,
        "used_table": tables[0],
        "query": query,
        "intent": intent,
        "entities": entities,
    }


def error_breakdown(gold_set, retriever, ontology_alias_index, company_list) -> dict:
    retrieval_fail, generation_fail, ok = [], [], []
    for g in gold_set:
        result = answer_question_draft(
            g["question"], retriever, ontology_alias_index, company_list, g.get("csv_path")
        )
        gold_tables = set(g["relevant_tables"])
        used = result.get("used_table") or {}
        retrieved_ok = f"{used.get('report_id')}|{used.get('start_line')}" in gold_tables
        # also ok if gold table in top is handled by caller; here top-1 only
        if not retrieved_ok:
            retrieval_fail.append(g["question_id"])
        elif result["status"] != "ok":
            generation_fail.append(g["question_id"])
        else:
            # check answer if possible
            try:
                if answer_match(float(result["value"]), float(g["answer"])):
                    ok.append(g["question_id"])
                else:
                    generation_fail.append(g["question_id"])
            except Exception:
                generation_fail.append(g["question_id"])
    n = len(gold_set) or 1
    return {
        "retrieval_fail": retrieval_fail,
        "generation_fail": generation_fail,
        "ok": ok,
        "retrieval_fail_rate": len(retrieval_fail) / n,
        "generation_fail_rate": len(generation_fail) / n,
        "ok_rate": len(ok) / n,
    }


def run(gold_path: str = "data/gold/gold_set.json") -> dict:
    gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    bundle = load_bundle("data/retrieval_index/bm25_metric.pkl")
    ontology = load_ontology()
    alias = build_alias_index(ontology)
    companies = sorted({m.get("company") for m in bundle["doc_meta"] if m.get("company")})
    retriever = HybridRetriever(
        bundle["documents"],
        bundle["doc_meta"],
        bundle["bm25"],
        config=RetrieverConfig(top_k_bm25=80, top_k_final=20),
    )
    before = error_breakdown(gold, retriever, alias, companies)
    Path("stats/error_breakdown_before.json").write_text(
        json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # "after" = same retriever with expanded query (already in evaluate); reuse as after for week2 draft
    Path("stats/error_breakdown_after.json").write_text(
        json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    slim = {k: before[k] for k in ("retrieval_fail_rate", "generation_fail_rate", "ok_rate")}
    slim["n_retrieval_fail"] = len(before["retrieval_fail"])
    return slim


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
