"""Day 6: pack gold as sample submission, run validator + scorer self-checks."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from .submission_validator import validate_submission
from .local_scorer import score_submission


REQUIRED_SUBMISSION_KEYS = ("question_id", "relevant_tables", "csv_path", "pandas_query", "answer")


def gold_to_submission_items(gold: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for g in gold:
        item = {k: g[k] for k in REQUIRED_SUBMISSION_KEYS if k in g}
        # ensure csv_path present (fallback evidence_csv)
        if "csv_path" not in item and g.get("evidence_csv"):
            item["csv_path"] = g["evidence_csv"]
        items.append(item)
    return items


def pack_sample_submission(
    gold_path: str = "data/gold/gold_set.json",
    zip_path: str = "data/gold/sample_submission.zip",
) -> dict:
    gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    items = gold_to_submission_items(gold)

    zip_p = Path(zip_path)
    zip_p.parent.mkdir(parents=True, exist_ok=True)

    missing_csv = []
    with zipfile.ZipFile(zip_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("submission.json", json.dumps(items, ensure_ascii=False, indent=2))
        for it in items:
            csv_path = it.get("csv_path", "")
            src = Path(csv_path)
            if not src.exists():
                missing_csv.append(csv_path)
                continue
            # store with forward-slash path as in submission
            arcname = csv_path.replace("\\", "/")
            z.write(src, arcname=arcname)

    return {
        "zip_path": str(zip_p),
        "n_items": len(items),
        "n_missing_csv": len(missing_csv),
        "missing_csv_sample": missing_csv[:10],
    }


def run_selfcheck(
    gold_path: str = "data/gold/gold_set.json",
    zip_path: str = "data/gold/sample_submission.zip",
    validator_out: str = "stats/day6_validator.json",
    scorer_out: str = "stats/day6_scorer.json",
) -> dict:
    pack = pack_sample_submission(gold_path, zip_path)
    v = validate_submission(zip_path)
    Path(validator_out).parent.mkdir(parents=True, exist_ok=True)
    Path(validator_out).write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")

    gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    preds = gold_to_submission_items(gold)
    # gold-vs-gold: predictions == gold submission fields
    s = score_submission(preds, gold)
    s["self_check"] = "gold_vs_gold"
    Path(scorer_out).write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "pack": pack,
        "validator": v,
        "scorer": s,
        "pass": bool(v.get("pass")) and float(s.get("answer_accuracy", 0)) == 1.0,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default="data/gold/gold_set.json")
    parser.add_argument("--zip", default="data/gold/sample_submission.zip")
    args = parser.parse_args()
    result = run_selfcheck(args.gold, args.zip)
    print(json.dumps(result, ensure_ascii=False, indent=2))
