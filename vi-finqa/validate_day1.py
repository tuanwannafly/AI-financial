import json
from pathlib import Path


def validate_day1(raw_dir: str = "data/raw", notes_path: str = "notes/data_exploration.md") -> dict:
    raw_root = Path(raw_dir)
    txt_files = list(raw_root.rglob("*.txt"))
    notes_file = Path(notes_path)

    result = {
        "raw_non_empty": bool(txt_files),
        "n_txt_files": len(txt_files),
        "notes_exists": notes_file.exists(),
        "n_file_blocks": 0,
        "n_ocr_issue_lines": 0,
        "pass": False,
    }

    if notes_file.exists():
        content = notes_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in content:
            if line.startswith("## File:"):
                result["n_file_blocks"] += 1
            if line.startswith("- OCR issues quan sát:") or "OCR issues quan sát" in line:
                # crude count of issues lines
                result["n_ocr_issue_lines"] += 1

    result["pass"] = (
        result["raw_non_empty"]
        and result["n_txt_files"] > 0
        and result["notes_exists"]
        and result["n_file_blocks"] >= 15
        and result["n_ocr_issue_lines"] >= 3
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", default="data/raw")
    parser.add_argument("--notes", default="notes/data_exploration.md")
    args = parser.parse_args()
    res = validate_day1(args.raw_dir, args.notes)
    print(json.dumps(res, ensure_ascii=False, indent=2))
