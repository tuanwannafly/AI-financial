import json
from pathlib import Path


def validate_day7(
    report_path: str = "docs/week1_report.md",
    final_status: str = "status/week1_final_status.md",
) -> dict:
    report = Path(report_path)
    status = Path(final_status)
    result = {
        "report_exists": report.exists(),
        "final_status_exists": status.exists(),
        "report_has_metrics": False,
        "backup_exists": False,
        "pass": False,
    }
    if report.exists():
        text = report.read_text(encoding="utf-8", errors="ignore")
        result["report_has_metrics"] = (
            "Coverage extraction" in text
            and "Gold set" in text
            and "Validator" in text
        )
    backups = list(Path("backups").glob("week1_*")) if Path("backups").exists() else []
    result["backup_exists"] = len(backups) > 0
    result["backup_files"] = [str(b) for b in backups[:5]]
    result["pass"] = (
        result["report_exists"]
        and result["final_status_exists"]
        and result["report_has_metrics"]
        and result["backup_exists"]
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="docs/week1_report.md")
    parser.add_argument("--status", default="status/week1_final_status.md")
    args = parser.parse_args()
    print(json.dumps(validate_day7(args.report, args.status), ensure_ascii=False, indent=2))
