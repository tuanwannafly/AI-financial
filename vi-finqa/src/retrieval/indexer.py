from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import List

from rank_bm25 import BM25Okapi


_TOKEN = re.compile(r"[A-Za-zÀ-ỹ0-9%]+", re.UNICODE)


def tokenize_vi(text: str) -> list[str]:
    """Lightweight tokenizer (no underthesea required)."""
    return [t.lower() for t in _TOKEN.findall(text or "")]


def build_bm25_index(documents: list[str]) -> BM25Okapi:
    return BM25Okapi([tokenize_vi(d) for d in documents])


def save_bundle(path: str, documents: list, doc_meta: list, bm25: BM25Okapi) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        pickle.dump({"documents": documents, "doc_meta": doc_meta, "bm25": bm25}, f)


def load_bundle(path: str) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)
