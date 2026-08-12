from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


def list_report_files(raw_dir: str) -> list[Path]:
    root = Path(raw_dir)
    return [
        p
        for p in root.rglob("*.txt")
        if "_smoke" not in str(p).replace("\\", "/")
        and "financial_statements" in str(p).replace("\\", "/")
    ]


def build_report(
    metadata_path: str = "data/extracted/metadata.jsonl",
    raw_dir: str = "data/raw",
    out_path: str = "stats/extraction_report.json",
    checkpoint_path: str = "checkpoints/day3.json",
) -> dict:
    raw_files = list_report_files(raw_dir)
    stems = {p.stem for p in raw_files}
    total = len(raw_files)

    files_with_tables: set[str] = set()
    type_counts: Counter = Counter()
    company_counts: Counter = Counter()
    tables_per_file: Counter = Counter()
    n_tables = 0
    n_with_unit = 0
    n_main = 0  # CDKT|KQKD|LCTT

    meta = Path(metadata_path)
    if meta.exists():
        with meta.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                n_tables += 1
                rid = rec.get("report_id")
                if rid:
                    files_with_tables.add(rid)
                    tables_per_file[rid] += 1
                ttype = rec.get("table_type", "UNKNOWN")
                type_counts[ttype] += 1
                if ttype in ("CDKT", "KQKD", "LCTT"):
                    n_main += 1
                if rec.get("unit"):
                    n_with_unit += 1
                co = rec.get("company")
                if co:
                    company_counts[co] += 1

    # only count stems that exist in raw
    extracted_stems = files_with_tables & stems
    extracted = len(extracted_stems)
    empty_stems = sorted(stems - extracted_stems)

    # files that have at least one main statement table
    main_files = set()
    if meta.exists():
        with meta.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("table_type") in ("CDKT", "KQKD", "LCTT") and rec.get("report_id") in stems:
                    main_files.add(rec["report_id"])

    ckpt_n = 0
    ckpt = Path(checkpoint_path)
    if ckpt.exists():
        try:
            ckpt_n = len(json.loads(ckpt.read_text(encoding="utf-8")))
        except Exception:
            ckpt_n = 0

    coverage = extracted / total if total else 0.0
    main_coverage = len(main_files) / total if total else 0.0

    # distribution of tables/file
    tpf_vals = list(tables_per_file.values())
    tpf_vals.sort()

    def percentile(vals, p):
        if not vals:
            return 0
        i = min(len(vals) - 1, max(0, int(round((p / 100) * (len(vals) - 1)))))
        return vals[i]

    report = {
        "total_files": total,
        "files_with_tables": extracted,
        "files_empty": len(empty_stems),
        "coverage": coverage,
        "main_statement_file_coverage": main_coverage,
        "n_tables": n_tables,
        "n_main_tables": n_main,
        "n_with_unit": n_with_unit,
        "by_table_type": dict(type_counts),
        "n_companies_in_tables": len(company_counts),
        "checkpoint_done": ckpt_n,
        "tables_per_file": {
            "min": tpf_vals[0] if tpf_vals else 0,
            "p50": percentile(tpf_vals, 50),
            "p90": percentile(tpf_vals, 90),
            "max": tpf_vals[-1] if tpf_vals else 0,
            "mean": round(sum(tpf_vals) / len(tpf_vals), 2) if tpf_vals else 0,
        },
        "empty_sample": empty_stems[:30],
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if empty_stems:
        Path("stats/day3_empty_files.json").write_text(
            json.dumps(empty_stems, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", default="data/extracted/metadata.jsonl")
    parser.add_argument("--raw_dir", default="data/raw")
    parser.add_argument("--out", default="stats/extraction_report.json")
    args = parser.parse_args()
    print(json.dumps(build_report(args.metadata, args.raw_dir, args.out), ensure_ascii=False, indent=2))
