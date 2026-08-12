import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List


REQUIRED_KEYS = {"question_id", "relevant_tables", "csv_path", "pandas_query", "answer"}


def validate_submission(zip_path: str) -> Dict[str, Any]:
    errors: List[str] = []
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if "submission.json" not in names:
            return {"pass": False, "errors": ["submission.json không tồn tại trong zip"]}
        data = json.loads(z.read("submission.json"))
        for i, item in enumerate(data):
            missing = REQUIRED_KEYS - item.keys()
            if missing:
                errors.append(f"item {i}: thiếu field {missing}")
            csv_path = item.get("csv_path", "")
            if csv_path and not csv_path.startswith("data/"):
                errors.append(f"item {i}: csv_path '{csv_path}' phải bắt đầu bằng 'data/'")
            if csv_path and csv_path not in names:
                errors.append(f"item {i}: csv_path '{csv_path}' không tồn tại trong zip")
            for t in item.get("relevant_tables", []):
                if "|" not in t:
                    errors.append(f"item {i}: relevant_table '{t}' sai format 'id|line'")
    return {"pass": len(errors) == 0, "errors": errors, "n_checked": len(data)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    args = parser.parse_args()
    result = validate_submission(args.zip_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
