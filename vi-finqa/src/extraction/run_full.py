from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

import jsonlines
from joblib import Parallel, delayed

from .table_extractor import extract_tables, table_record_to_dict


CHECKPOINT = Path("checkpoints/day3.json")


def _norm_key(path: Path, raw_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(raw_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def list_report_files(raw_dir: str) -> List[Path]:
    root = Path(raw_dir)
    return sorted(
        p
        for p in root.rglob("*.txt")
        if "_smoke" not in str(p).replace("\\", "/")
        and "financial_statements" in str(p).replace("\\", "/")
    )


def load_checkpoint() -> set[str]:
    if CHECKPOINT.exists():
        return set(json.loads(CHECKPOINT.read_text(encoding="utf-8")))
    return set()


def save_checkpoint(done: set[str]) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8")


def process_one(f: Path) -> tuple[str, list[dict], float]:
    t0 = time.time()
    recs = extract_tables(f, report_id=f.stem)
    return f.stem, [table_record_to_dict(r) for r in recs], time.time() - t0


def run_full(
    raw_dir: str,
    n_jobs: int = 4,
    out_path: str = "data/extracted/metadata.jsonl",
    batch_size: int = 100,
    reset: bool = False,
) -> dict:
    raw_root = Path(raw_dir)
    files = list_report_files(raw_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if reset:
        if out.exists():
            out.unlink()
        if CHECKPOINT.exists():
            CHECKPOINT.unlink()

    done = load_checkpoint()
    # map key -> path
    key_to_path = {_norm_key(f, raw_root): f for f in files}
    # also accept stem-only legacy keys
    todo_keys = [k for k in key_to_path if k not in done]
    # if checkpoint stored absolute paths previously
    if not todo_keys and done:
        abs_done = {str(Path(x)).replace("\\", "/") for x in done}
        todo_keys = [
            k
            for k, p in key_to_path.items()
            if k not in done and str(p.resolve()).replace("\\", "/") not in abs_done
        ]

    todo = [key_to_path[k] for k in todo_keys]
    n_empty = 0
    n_tables = 0
    t_start = time.time()

    log_path = Path("logs/day3_run.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(event: dict) -> None:
        event = dict(event)
        event.setdefault("ts", time.time())
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(json.dumps(event, ensure_ascii=False) + "\n")

    log({"event": "run_start", "n_files": len(files), "n_todo": len(todo), "n_done": len(done), "jobs": n_jobs})

    mode = "a" if out.exists() and not reset else "w"
    with jsonlines.open(out, mode=mode) as writer:
        for batch_start in range(0, len(todo), batch_size):
            batch = todo[batch_start : batch_start + batch_size]
            batch_t0 = time.time()
            if n_jobs <= 1:
                results = [process_one(f) for f in batch]
            else:
                results = Parallel(n_jobs=n_jobs, prefer="processes")(
                    delayed(process_one)(f) for f in batch
                )
            for f, (stem, recs, _dt) in zip(batch, results):
                for r in recs:
                    # keep raw_text truncated already; drop huge rows? keep as is
                    writer.write(r)
                n_tables += len(recs)
                if not recs:
                    n_empty += 1
                done.add(_norm_key(f, raw_root))
            save_checkpoint(done)
            log(
                {
                    "event": "batch_done",
                    "batch_start": batch_start,
                    "batch_size": len(batch),
                    "done": len(done),
                    "n_tables_cum": n_tables,
                    "n_empty_cum": n_empty,
                    "batch_sec": round(time.time() - batch_t0, 2),
                }
            )

    elapsed = time.time() - t_start
    summary = {
        "n_files": len(files),
        "n_processed_this_run": len(todo),
        "n_done_total": len(done),
        "n_tables_written": n_tables,
        "n_empty_files": n_empty,
        "elapsed_sec": round(elapsed, 2),
        "out_path": str(out),
    }
    log({"event": "run_end", **summary})
    Path("stats/day3_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--out", default="data/extracted/metadata.jsonl")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    summary = run_full(
        args.raw_dir,
        n_jobs=args.jobs,
        out_path=args.out,
        batch_size=args.batch_size,
        reset=args.reset,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
