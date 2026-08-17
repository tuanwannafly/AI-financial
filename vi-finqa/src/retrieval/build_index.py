"""Build retrieval corpus from long_format_mapped clusters + pickle BM25."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ..schema.normalize import build_alias_index, load_ontology
from .indexer import build_bm25_index, save_bundle
from .represent import build_doc_from_long_cluster


def build_corpus(
    long_path: str = "data/processed/long_format_mapped.jsonl",
    out_path: str = "data/retrieval_index/bm25_bundle.pkl",
) -> dict:
    clusters: dict[tuple, list] = defaultdict(list)
    with open(long_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r.get("report_id"), r.get("start_line"), r.get("company"), r.get("năm"))
            clusters[key].append(r)

    ontology = load_ontology()
    alias = build_alias_index(ontology)
    documents, metas = [], []
    for (rid, sl, co, year), rows in clusters.items():
        if not rid:
            continue
        doc = build_doc_from_long_cluster(rows, alias)
        documents.append(doc)
        metas.append(
            {
                "report_id": rid,
                "start_line": sl,
                "company": co,
                "year": int(year) if year is not None else None,
                "table_type": rows[0].get("table_type"),
                "table_key": f"{rid}|{sl}",
                "n_rows": len(rows),
            }
        )

    bm25 = build_bm25_index(documents)
    save_bundle(out_path, documents, metas, bm25)
    return {"n_docs": len(documents), "out_path": out_path}


if __name__ == "__main__":
    print(json.dumps(build_corpus(), ensure_ascii=False, indent=2))
