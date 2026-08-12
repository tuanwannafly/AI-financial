import json
from pathlib import Path


def validate_day2(stats_path: str = "stats/day2_coverage.json", threshold: float = 0.70) -> dict:
    stats_file = Path(stats_path)
    if not stats_file.exists():
        return {"pass": False, "reason": f"missing {stats_path}"}

    data = json.loads(stats_file.read_text(encoding="utf-8"))
    coverage = float(data.get("coverage", 0.0))
    return {"pass": coverage >= threshold, "coverage": coverage, "threshold": threshold}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", default="stats/day2_coverage.json")
    parser.add_argument("--threshold", type=float, default=0.70)
    args = parser.parse_args()
    res = validate_day2(args.stats, args.threshold)
    print(json.dumps(res, ensure_ascii=False, indent=2))
