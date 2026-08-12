import json
from pathlib import Path


def validate_day6(
    validator_result: str = "stats/day6_validator.json",
    scorer_result: str = "stats/day6_scorer.json",
) -> dict:
    out = {"pass": False, "validator": None, "scorer": None}

    vpath = Path(validator_result)
    spath = Path(scorer_result)
    if not vpath.exists() or not spath.exists():
        out["reason"] = "missing day6 stats files — run selfcheck first"
        return out

    v = json.loads(vpath.read_text(encoding="utf-8"))
    s = json.loads(spath.read_text(encoding="utf-8"))
    out["validator"] = v
    out["scorer"] = s
    out["pass"] = bool(v.get("pass")) and float(s.get("answer_accuracy", 0)) == 1.0
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--validator", default="stats/day6_validator.json")
    parser.add_argument("--scorer", default="stats/day6_scorer.json")
    args = parser.parse_args()
    print(json.dumps(validate_day6(args.validator, args.scorer), ensure_ascii=False, indent=2))
