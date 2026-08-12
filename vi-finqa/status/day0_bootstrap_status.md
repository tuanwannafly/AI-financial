# Day 0 / Bootstrap Status — PASS

## Done
- Repo skeleton under `vi-finqa/` (dirs depth≤2 ≥15)
- `requirements.txt` installed via `py -m pip` (pandas, rapidfuzz, datasets, jsonlines, …)
- `py validate_repo.py` → **PASS**
- All `*.py` syntax OK
- Fixed bugs from initial scaffold:
  - `NEGATIVE_NUM` regex broken across lines in `table_extractor.py`
  - missing `Path` import in `local_scorer.py` `__main__`
- Modules:
  - utils: download, sample_explore, list_files, logging_utils, run_day1_explore
  - extraction: table_extractor, test_coverage, run_full, llm_refine, build_extraction_report
  - schema: ontology.yaml, normalize, run_normalize
  - gold: build_gold_helpers
  - validators + day1–day7 validate scripts
- Smoke sample dir ready: `data/raw/_smoke/` (created by smoke script)

## Blocked / next
- **Day 1**: need HuggingFace `repo_id` for ViFinQA (not in plan). Place files in `data/raw/` then:
  ```powershell
  cd vi-finqa
  py -m src.utils.run_day1_explore --raw_dir data/raw --n 25
  py validate_day1.py
  ```
- Use `py` not `python` on this machine.

## Escalate rules
See plan §0 and `docs/ESCALATION_TEMPLATE.md`.
