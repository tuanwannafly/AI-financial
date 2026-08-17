import json
from pathlib import Path

import yaml


def count_jsonl(p: str) -> int:
    path = Path(p)
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def validate() -> dict:
    tax = yaml.safe_load(Path("src/synthetic/taxonomy.yaml").read_text(encoding="utf-8"))
    n_syn = count_jsonl("data/synthetic/verified_v1.jsonl") + count_jsonl("data/synthetic/holdout_val.jsonl")
    ev = {}
    ep = Path("stats/retrieval_eval_summary.json")
    if ep.exists():
        ev = json.loads(ep.read_text(encoding="utf-8"))
    report = Path("docs/week2_report.md").exists()
    final = Path("status/week2_final_status.md").exists()
    r20 = float(ev.get("recall@20") or 0)
    result = {
        "taxonomy_n": len(tax or {}),
        "n_synthetic": n_syn,
        "recall@20": r20,
        "report": report,
        "final_status": final,
        "pass": (
            len(tax or {}) >= 10
            and n_syn >= 5000
            and r20 >= 0.70
            and report
            and final
        ),
    }
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
