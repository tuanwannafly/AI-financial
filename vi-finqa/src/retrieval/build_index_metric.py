"""Finer corpus: one document per (table, canonical-or-raw term)."""
from __future__ import annotations

import json
from pathlib import Path

from .indexer import build_bm25_index, save_bundle


def build_metric_corpus(
    long_path: str = "data/processed/long_format_mapped.jsonl",
    out_path: str = "data/retrieval_index/bm25_metric.pkl",
    max_docs: int | None = None,
) -> dict:
    documents, metas = [], []
    seen = set()
    with open(long_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            rid, sl = r.get("report_id"), r.get("start_line")
            if not rid:
                continue
            can = r.get("canonical") or r.get("chỉ_tiêu") or ""
            key = (rid, sl, can, r.get("năm"))
            if key in seen or not can:
                continue
            seen.add(key)
            doc = (
                f"Công ty {r.get('company','')} ticker {r.get('company','')} "
                f"năm {r.get('năm','')} {r.get('table_type','')} "
                f"{can} {r.get('chỉ_tiêu','')} "
                f"report {rid}"
            )
            documents.append(doc)
            metas.append(
                {
                    "report_id": rid,
                    "start_line": sl,
                    "company": r.get("company"),
                    "year": r.get("năm"),
                    "table_type": r.get("table_type"),
                    "table_key": f"{rid}|{sl}",
                    "canonical": can,
                }
            )
            if max_docs is not None and len(documents) >= max_docs:
                break

    bm25 = build_bm25_index(documents)
    save_bundle(out_path, documents, metas, bm25)
    return {"n_docs": len(documents), "out_path": out_path}


if __name__ == "__main__":
    print(json.dumps(build_metric_corpus(), ensure_ascii=False, indent=2))
