"""Structural and semantic checks for the official submission format."""
from __future__ import annotations

import ast
import json
import keyword
import re
import zipfile
from typing import Any


OFFICIAL_KEYS = {
    "id",
    "question",
    "answer",
    "relevant_docs",
    "relevant_tables",
    "evidence",
    "pandas_query",
}
LEGACY_KEYS = {"question_id", "relevant_tables", "csv_path", "pandas_query", "answer"}
SAFE_PATH_RE = re.compile(r"^data/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.csv$")


def _error(errors: list[str], index: int, message: str) -> None:
    errors.append(f"item {index}: {message}")


def _valid_python_identifier(value: Any) -> bool:
    return isinstance(value, str) and value.isidentifier() and not keyword.iskeyword(value)


def _check_query(query: Any) -> str | None:
    if not isinstance(query, str) or not query.strip():
        return "pandas_query phải là chuỗi không rỗng"
    try:
        tree = ast.parse(query, mode="exec")
    except SyntaxError as exc:
        return f"pandas_query lỗi cú pháp: {exc.msg}"
    banned = ("Import", "ImportFrom", "With", "Try", "FunctionDef", "ClassDef")
    if any(type(node).__name__ in banned for node in ast.walk(tree)):
        return "pandas_query chứa cấu trúc không được phép"
    return None


def _paths_for_item(item: dict) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for evidence in item.get("evidence") or []:
        if isinstance(evidence, dict):
            paths.append((str(evidence.get("variable") or ""), str(evidence.get("csv_path") or "")))
    if not paths and item.get("csv_path"):
        paths.append(("df", str(item.get("csv_path"))))
    return paths


def validate_submission(zip_path: str, expected_n: int | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        archive = zipfile.ZipFile(zip_path)
    except (FileNotFoundError, zipfile.BadZipFile) as exc:
        return {"pass": False, "errors": [str(exc)], "warnings": []}

    with archive as z:
        names = z.namelist()
        json_names = [name for name in names if name.lower().endswith(".json")]
        if "submission.json" not in names:
            return {"pass": False, "errors": ["submission.json không tồn tại"], "warnings": []}
        if json_names != ["submission.json"]:
            errors.append("ZIP chỉ được chứa một file JSON là submission.json")
        if any(name.startswith("/") or ".." in name.split("/") for name in names):
            errors.append("ZIP chứa đường dẫn không an toàn")
        if any(name != "submission.json" and not SAFE_PATH_RE.fullmatch(name) for name in names):
            errors.append("ZIP có file ngoài submission.json hoặc data/*.csv")

        try:
            data = json.loads(z.read("submission.json"))
        except Exception as exc:
            return {"pass": False, "errors": [f"submission.json không hợp lệ: {exc}"], "warnings": []}
        if not isinstance(data, list):
            return {"pass": False, "errors": ["submission.json phải là một mảng JSON"], "warnings": []}
        if expected_n is not None and len(data) != expected_n:
            errors.append(f"số câu {len(data)} khác expected_n={expected_n}")

        ids: list[int] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                _error(errors, index, "item phải là object")
                continue
            official = "id" in item or "evidence" in item
            required = OFFICIAL_KEYS if official else LEGACY_KEYS
            missing = required - item.keys()
            if missing:
                _error(errors, index, f"thiếu field {sorted(missing)}")
            if official:
                if not isinstance(item.get("id"), int) or isinstance(item.get("id"), bool):
                    _error(errors, index, "id phải là integer")
                else:
                    ids.append(item["id"])
                if not isinstance(item.get("answer"), (int, float)) or isinstance(item.get("answer"), bool):
                    _error(errors, index, "answer phải là số")
                if not isinstance(item.get("relevant_docs"), list) or not isinstance(item.get("relevant_tables"), list):
                    _error(errors, index, "relevant_docs/relevant_tables phải là list")
                table_keys = item.get("relevant_tables") or []
                if len(table_keys) != len(set(table_keys)):
                    _error(errors, index, "relevant_tables bị trùng")
            paths = _paths_for_item(item)
            variables = [variable for variable, _ in paths]
            if len(variables) != len(set(variables)):
                _error(errors, index, "tên biến evidence bị trùng")
            for variable, csv_path in paths:
                if not _valid_python_identifier(variable):
                    _error(errors, index, f"variable không hợp lệ: {variable!r}")
                if not SAFE_PATH_RE.fullmatch(csv_path):
                    _error(errors, index, f"csv_path không hợp lệ: {csv_path!r}")
                if csv_path not in names:
                    _error(errors, index, f"csv_path không tồn tại trong ZIP: {csv_path!r}")
            query_error = _check_query(item.get("pandas_query"))
            if query_error:
                _error(errors, index, query_error)
            if official and not item.get("relevant_tables"):
                warnings.append(f"item {index}: không có relevant_tables grounded")
        if len(ids) != len(set(ids)):
            errors.append("id bị trùng")
        if expected_n is not None and ids and ids != list(range(1, expected_n + 1)):
            errors.append("id không liên tục từ 1 đến expected_n")

    return {"pass": not errors, "errors": errors, "warnings": warnings, "n_checked": len(data) if isinstance(data, list) else 0}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--expected-n", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(validate_submission(args.zip_path, args.expected_n), ensure_ascii=False, indent=2))
