import json
from pathlib import Path

MIN_COVERAGE = 0.85
MIN_GOLD_N = 120


def audit_week1(
    report_path: str = "stats/extraction_report.json",
    gold_path: str = "data/gold/gold_set.json",
) -> dict:
    rp = Path(report_path)
    gp = Path(gold_path)
    coverage = json.loads(rp.read_text(encoding="utf-8"))["coverage"] if rp.exists() else 0.0
    gold = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else []
    gold_n = len(gold)
    verified_ratio = (
        sum(1 for g in gold if g.get("verified_by_execution")) / gold_n if gold_n else 0.0
    )
    ok = coverage >= MIN_COVERAGE and gold_n >= MIN_GOLD_N and verified_ratio >= 0.95
    return {
        "coverage": coverage,
        "gold_n": gold_n,
        "verified_ratio": verified_ratio,
        "ok_to_proceed": ok,
        "action": "proceed_to_week2" if ok else "patch_week1_first",
    }


if __name__ == "__main__":
    print(json.dumps(audit_week1(), ensure_ascii=False, indent=2))
