import json
from pathlib import Path

from .submission_validator import validate_submission


def run_selfcheck(sample_zip: str = "data/gold/sample_submission.zip") -> dict:
    zip_path = Path(sample_zip)
    if not zip_path.exists():
        return {"pass": False, "reason": f"missing {sample_zip}"}
    return validate_submission(str(zip_path))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", default="data/gold/sample_submission.zip")
    args = parser.parse_args()
    res = run_selfcheck(args.zip)
    print(json.dumps(res, ensure_ascii=False, indent=2))
