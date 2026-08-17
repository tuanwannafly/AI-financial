from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from .indexer import tokenize_vi


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


@dataclass
class RetrieverConfig:
    top_k_bm25: int = 30
    top_k_dense: int = 30
    top_k_final: int = 20
    rrf_k: int = 60


class HybridRetriever:
    def __init__(
        self,
        documents,
        doc_meta,
        bm25_index,
        dense_index=None,
        dense_model=None,
        config: RetrieverConfig | None = None,
    ):
        self.documents = documents
        self.doc_meta = doc_meta
        self.bm25 = bm25_index
        self.dense_index = dense_index
        self.dense_model = dense_model
        self.config = config or RetrieverConfig()

    def retrieve(self, query: str, filters: dict | None = None) -> list[dict]:
        bm25_scores = self.bm25.get_scores(tokenize_vi(query))
        # optional company prefilter via large candidate pool
        bm25_rank = np.argsort(-bm25_scores)[: max(self.config.top_k_bm25, 80)].tolist()

        rankings = [bm25_rank]
        if self.dense_index is not None and self.dense_model is not None:
            q_emb = self.dense_model.encode([query], normalize_embeddings=True).astype("float32")
            _, dense_rank = self.dense_index.search(q_emb, self.config.top_k_dense)
            rankings.append(dense_rank[0].tolist())

        fused = reciprocal_rank_fusion(rankings, k=self.config.rrf_k)
        results = []
        for idx, score in fused:
            meta = dict(self.doc_meta[idx])
            if filters and filters.get("company") and meta.get("company") != filters["company"]:
                continue
            if filters and filters.get("year") is not None and meta.get("year") != filters["year"]:
                continue
            meta["score"] = float(score)
            results.append(meta)
            if len(results) >= self.config.top_k_final:
                break
        return results
