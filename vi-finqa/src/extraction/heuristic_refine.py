"""Post-pass refine for low-confidence tables without requiring LLM.

Re-labels UNKNOWN using row content; drops non-financial junk.
Optional Anthropic call if ANTHROPIC_API_KEY is set (see llm_refine).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .table_extractor import infer_type_from_rows, _is_financial_table, _is_toc_table
from .llm_refine import needs_llm_assist, build_verify_prompt, parse_llm_json


def refine_record(rec: Dict[str, Any]) -> Dict[str, Any] | None:
    rows = rec.get("rows") or []
    if _is_toc_table(rows):
        return None
    ttype = rec.get("table_type") or "UNKNOWN"
    if ttype in (None, "UNKNOWN") or needs_llm_assist(rec):
        inferred = infer_type_from_rows(rows)
        if inferred not in (None, "UNKNOWN", "TOC"):
            rec = dict(rec)
            rec["table_type"] = inferred
            rec["refined"] = "heuristic"
            ttype = inferred
    if ttype in (None, "UNKNOWN", "TOC") and not _is_financial_table(rows):
        return None
    return rec


def refine_metadata(
    in_path: str = "data/extracted/metadata.jsonl",
    out_path: str = "data/extracted/metadata.jsonl",
) -> dict:
    src = Path(in_path)
    if not src.exists():
        return {"pass": False, "reason": "missing metadata"}

    kept: List[dict] = []
    dropped = 0
    relabeled = 0
    with src.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            before = rec.get("table_type")
            out = refine_record(rec)
            if out is None:
                dropped += 1
                continue
            if out.get("table_type") != before:
                relabeled += 1
            kept.append(out)

    # write to temp then replace
    tmp = Path(str(out_path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as w:
        for rec in kept:
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(out_path)
    return {
        "n_kept": len(kept),
        "n_dropped": dropped,
        "n_relabeled": relabeled,
        "out_path": out_path,
    }


def maybe_llm_refine_sample(records: Iterable[dict], limit: int = 20) -> list[dict]:
    """If ANTHROPIC_API_KEY present, refine up to `limit` low-confidence records."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return []
    try:
        import anthropic
    except ImportError:
        return []

    client = anthropic.Anthropic(api_key=key)
    updated = []
    n = 0
    for rec in records:
        if not needs_llm_assist(rec):
            continue
        prompt = build_verify_prompt(
            rec.get("report_id", ""),
            rec.get("start_line", 0),
            rec.get("end_line", 0),
            rec.get("raw_text") or "",
        )
        try:
            msg = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=300,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}],
            )
            text = msg.content[0].text if msg.content else ""
            parsed = parse_llm_json(text)
            if not parsed:
                continue
            rec = dict(rec)
            if parsed.get("table_type"):
                rec["table_type"] = parsed["table_type"]
            if "unit" in parsed and parsed["unit"]:
                rec["unit"] = parsed["unit"]
            if parsed.get("is_valid_table") is False:
                continue
            rec["refined"] = "llm"
            updated.append(rec)
            n += 1
            if n >= limit:
                break
        except Exception:
            continue
    return updated


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="data/extracted/metadata.jsonl")
    parser.add_argument("--out", dest="out_path", default="data/extracted/metadata.jsonl")
    args = parser.parse_args()
    print(json.dumps(refine_metadata(args.in_path, args.out_path), ensure_ascii=False, indent=2))
