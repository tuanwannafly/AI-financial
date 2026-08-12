import json
from pathlib import Path

from .local_scorer import score_submission


def run_selfcheck(pred_path: str = "data/gold/gold_set.json", gold_path: str = "data/gold/gold_set.json") -> dict:
    pred_file = Path(pred_path)
    gold_file = Path(gold_path)
    if not pred_file.exists() or not gold_file.exists():
        return {"pass": False, "reason": "missing gold_set.json"}
    preds = json.loads(pred_file.read_text(encoding="utf-8"))
    gold = json.loads(gold_file.read_text(encoding="utf-8"))
    metrics = score_submission(preds, gold)
    metrics["pass"] = metrics.get("answer_accuracy", 0.0) == 1.0
    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", default="data/gold/gold_set.json")
    parser.add_argument("--gold", default="data/gold/gold_set.json")
    args = parser.parse_args()
    res = run_selfcheck(args.pred, args.gold)
    print(json.dumps(res, ensure_ascii=False, indent=2))
