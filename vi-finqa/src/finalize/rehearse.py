from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..pipeline.e2e import load_retriever, run_e2e
from ..schema.normalize import build_alias_index, load_ontology


def format_submission_entry(question_id: str, e2e_result: dict, fallback_csv: str = "") -> dict:
    tables = e2e_result.get("retrieved") or []
    table = tables[0] if tables else {}
    res = e2e_result.get("result") or {}
    csv_path = fallback_csv or table.get("csv_path") or "data/gold/evidence/q_0001.csv"
    keys = [f"{t.get('report_id')}|{t.get('start_line')}" for t in tables[:5] if t.get("report_id")]
    if not keys:
        keys = ["unknown|0"]
    return {
        "question_id": question_id,
        "relevant_tables": keys,
        "csv_path": csv_path.replace("\\", "/"),
        "pandas_query": res.get("code") or e2e_result.get("query") or "df['giá_trị'].iloc[0]",
        "answer": res.get("value"),
    }


def rehearse_submission(gold_set, out_zip="submissions/rehearsal.zip") -> dict:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from validators.submission_validator import validate_submission

    retriever, _, companies = load_retriever()
    ontology = load_ontology()
    alias = build_alias_index(ontology)
    entries, csv_paths = [], []
    for g in gold_set:
        e2e = run_e2e(
            g["question"],
            retriever,
            ontology,
            alias,
            companies,
            csv_path=g.get("csv_path"),
            use_repair=True,
        )
        entry = format_submission_entry(g["question_id"], e2e, g.get("csv_path", ""))
        entries.append(entry)
        if entry["csv_path"] and Path(entry["csv_path"]).exists():
            csv_paths.append(entry["csv_path"])
    Path(out_zip).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w") as z:
        z.writestr("submission.json", json.dumps(entries, ensure_ascii=False))
        for p in set(csv_paths):
            z.write(p, arcname=p.replace("\\", "/"))
    return validate_submission(out_zip)


if __name__ == "__main__":
    gold = json.loads(Path("data/gold/gold_set.json").read_text(encoding="utf-8"))
    print(json.dumps(rehearse_submission(gold), ensure_ascii=False, indent=2))
