import json
import random
from collections import Counter
from pathlib import Path

from .table_extractor import extract_tables


def _sample_files(sample_dir: str, n: int = 50, seed: int = 42) -> list[Path]:
    files = [
        p
        for p in Path(sample_dir).rglob("*.txt")
        if "_smoke" not in str(p).replace("\\", "/")
    ]
    rng = random.Random(seed)
    rng.shuffle(files)
    return files[:n]


def run_coverage_test(
    sample_dir: str,
    out_path: str = "stats/day2_coverage.json",
    n: int = 50,
    seed: int = 42,
) -> dict:
    files = _sample_files(sample_dir, n=n, seed=seed)
    total, extracted, fails = len(files), 0, []
    type_counts: Counter = Counter()
    n_tables = 0
    details = []

    for f in files:
        recs = extract_tables(f, report_id=f.stem)
        n_tables += len(recs)
        for r in recs:
            type_counts[r.table_type] += 1
        if recs:
            extracted += 1
            details.append({"file": str(f), "n_tables": len(recs), "types": [r.table_type for r in recs]})
        else:
            fails.append(str(f))

    result = {
        "total": total,
        "extracted": extracted,
        "coverage": extracted / total if total else 0.0,
        "n_tables": n_tables,
        "by_table_type": dict(type_counts),
        "fails": fails,
        "sample_ok": details[:10],
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("sample_dir", help="Directory with raw .txt samples")
    parser.add_argument("--out", default="stats/day2_coverage.json")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    res = run_coverage_test(args.sample_dir, args.out, args.n, args.seed)
    print(json.dumps({k: res[k] for k in ("total", "extracted", "coverage", "n_tables", "by_table_type", "fails")}, ensure_ascii=False, indent=2))
