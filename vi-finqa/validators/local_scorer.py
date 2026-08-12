from __future__ import annotations

from typing import List, Dict, Any, Set

import pandas as pd


def f2_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    beta2 = 4  # F2: recall được trọng số gấp đôi precision
    return (1 + beta2) * precision * recall / (beta2 * precision + recall)


def table_retrieval_score(predicted: Set[str], gold: Set[str]) -> Dict[str, float]:
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return {"precision": precision, "recall": recall, "f2": f2_score(precision, recall)}


def answer_match(pred: float, gold: float, abs_tol: float = 1.0, rel_tol: float = 0.001) -> bool:
    if abs(pred - gold) <= abs_tol:
        return True
    if gold != 0 and abs(pred - gold) / abs(gold) <= rel_tol:
        return True
    return False


def score_submission(predictions: List[Dict[str, Any]], gold_set: List[Dict[str, Any]]) -> Dict[str, Any]:
    gold_by_id = {g["question_id"]: g for g in gold_set}
    retrieval_scores, answer_hits, exec_hits = [], 0, 0
    for p in predictions:
        g = gold_by_id.get(p["question_id"])
        if not g:
            continue
        retrieval_scores.append(
            table_retrieval_score(set(p.get("relevant_tables", [])), set(g["relevant_tables"]))
        )
        try:
            result = eval(p["pandas_query"], {"df": pd.read_csv(p["csv_path"])})
            exec_hits += 1
            if answer_match(float(result), float(g["answer"])):
                answer_hits += 1
        except Exception:
            # execution fail: do not crash whole scorer
            continue

    n = len(predictions)
    return {
        "macro_f2": sum(s["f2"] for s in retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0,
        "answer_accuracy": answer_hits / n if n else 0,
        "execution_accuracy": exec_hits / n if n else 0,
        "n_scored": n,
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("predictions")
    parser.add_argument("gold")
    args = parser.parse_args()

    preds = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    result = score_submission(preds, gold)
    print(json.dumps(result, ensure_ascii=False, indent=2))
