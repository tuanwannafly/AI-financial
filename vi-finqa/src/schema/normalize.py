from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple, Any

import yaml
from rapidfuzz import process, fuzz

# strip leading numbering/letter prefixes like "1. ", "I. ", "A. ", "01. ", "3)"
PREFIX_RE = re.compile(
    r"^\s*(?:(?:[A-ZĐẠ-ỹ]+|[IVXMCivxmc]+|\d{1,3})[\.\):]\s*)+",
    re.IGNORECASE,
)
WS_RE = re.compile(r"\s+")


def strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clean_term(raw: str) -> str:
    t = PREFIX_RE.sub("", raw)
    t = WS_RE.sub(" ", t).strip()
    return t


def key_of(term: str) -> str:
    """Matching key: strip prefixes + diacritics, lowercase."""
    return strip_diacritics(clean_term(term)).lower()


def load_ontology(path: str = "src/schema/ontology.yaml") -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_alias_index(ontology: Dict[str, Any]) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for canon, meta in ontology.items():
        # canon key points at itself (or its canonical target)
        index[key_of(canon)] = canon
        for a in meta.get("aliases", []):
            index[key_of(a)] = canon
    return index


def normalize_term(raw_term: str, alias_index: Dict[str, str], threshold: int = 85) -> Tuple[str | None, float]:
    k = key_of(raw_term)
    if k in alias_index:
        return alias_index[k], 1.0
    match = process.extractOne(k, alias_index.keys(), scorer=fuzz.token_sort_ratio)
    if match is None:
        return None, 0.0
    key, score, _ = match
    if score >= threshold:
        return alias_index[key], score / 100
    return None, score / 100


def normalize_batch(raw_terms: List[str], ontology_path: str = "src/schema/ontology.yaml"):
    ontology = load_ontology(ontology_path)
    alias_index = build_alias_index(ontology)
    results, review_queue = [], []
    for term in raw_terms:
        canon, conf = normalize_term(term, alias_index)
        row = {"raw": term, "clean": clean_term(term), "canonical": canon, "confidence": conf}
        results.append(row)
        if conf < 0.7:
            review_queue.append(row)
    return results, review_queue
