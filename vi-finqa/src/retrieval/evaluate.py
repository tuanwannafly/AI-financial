from __future__ import annotations

import json
from pathlib import Path

from ..schema.normalize import build_alias_index, load_ontology
from .indexer import load_bundle
from .query_understanding import classify_intent, expand_query, extract_entities
from .retriever import HybridRetriever, RetrieverConfig


def recall_at_k(predicted: list[str], gold: set[str], k: int) -> float:
    return len(set(predicted[:k]) & gold) / len(gold) if gold else 0.0


def evaluate_retrieval(retriever, gold_set, ontology_alias_index, ontology, company_list) -> dict:
    rows = []
    nonempty = 0
    for g in gold_set:
        entities = extract_entities(g["question"], ontology_alias_index, company_list)
        intent = classify_intent(g["question"], entities)
        expanded = expand_query(g["question"], entities, ontology)
        filters = {"company": entities["companies"][0]} if entities["companies"] else None
        # inject years into query text instead of hard year filter
        # (gold tables often live in report year Y+1 for metric year Y)
        q2 = expanded
        if entities["years"]:
            q2 = expanded + " " + " ".join(str(y) for y in entities["years"])
        results = retriever.retrieve(q2, filters=filters)
        if results:
            nonempty += 1
        predicted = [f"{r['report_id']}|{r['start_line']}" for r in results]
        gold_tables = set(g.get("relevant_tables") or [])
        rows.append(
            {
                "question_id": g["question_id"],
                "intent": intent,
                "n_pred": len(predicted),
                "recall@5": recall_at_k(predicted, gold_tables, 5),
                "recall@10": recall_at_k(predicted, gold_tables, 10),
                "recall@20": recall_at_k(predicted, gold_tables, 20),
            }
        )
    import pandas as pd

    df = pd.DataFrame(rows)
    by_intent = df.groupby("intent")["recall@10"].mean().to_dict() if len(df) else {}
    return {
        "n": len(rows),
        "nonempty_rate": nonempty / len(rows) if rows else 0,
        "recall@5": float(df["recall@5"].mean()) if len(df) else 0,
        "recall@10": float(df["recall@10"].mean()) if len(df) else 0,
        "recall@20": float(df["recall@20"].mean()) if len(df) else 0,
        "by_intent": by_intent,
        "per_question": rows,
    }


def run_eval(
    gold_path: str = "data/gold/gold_set.json",
    bundle_path: str = "data/retrieval_index/bm25_metric.pkl",
    out_path: str = "stats/retrieval_eval.json",
) -> dict:
    gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    bundle = load_bundle(bundle_path)
    ontology = load_ontology()
    alias = build_alias_index(ontology)
    companies = sorted({m.get("company") for m in bundle["doc_meta"] if m.get("company")})
    retriever = HybridRetriever(
        bundle["documents"],
        bundle["doc_meta"],
        bundle["bm25"],
        config=RetrieverConfig(top_k_bm25=80, top_k_final=20, rrf_k=60),
    )
    result = evaluate_retrieval(retriever, gold, alias, ontology, companies)
    slim = {k: v for k, v in result.items() if k != "per_question"}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("stats/retrieval_eval_summary.json").write_text(
        json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    misses = [r for r in result["per_question"] if r["recall@20"] == 0]
    Path("stats/error_analysis.json").write_text(
        json.dumps({"n_miss_r20": len(misses), "sample": misses[:30]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return slim


if __name__ == "__main__":
    print(json.dumps(run_eval(), ensure_ascii=False, indent=2))
