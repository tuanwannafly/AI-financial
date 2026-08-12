# Week 1 Agent Checklist

## Day 0 — Bootstrap ✅
- [x] dirs + requirements
- [x] `validate_repo.py` PASS
- [x] skeleton modules

## Day 1 — Explore
- [ ] `py -m src.utils.download_cli --repo_id <HF_REPO>`
- [ ] `py -m src.utils.run_day1_explore --n 25`
- [ ] `py validate_day1.py` → PASS
- [ ] status: `status/day1_status.md`

## Day 2 — Heuristic extractor
- [ ] tune patterns from real samples
- [ ] `py -m src.extraction.test_coverage data/raw`
- [ ] `py validate_day2.py` (coverage ≥ 0.70)
- [ ] max 3 retry loops; else escalate

## Day 3 — Full run
- [ ] `py -m src.extraction.run_full data/raw`
- [ ] LLM-assist low-confidence tables (`src/extraction/llm_refine.py`)
- [ ] `py -m src.extraction.build_extraction_report`
- [ ] `py validate_day3.py` (coverage ≥ 0.90)

## Day 4 — Ontology
- [ ] expand `src/schema/ontology.yaml`
- [ ] `py -m src.schema.run_normalize`
- [ ] `py validate_day4.py`

## Day 5 — Gold set
- [ ] build ≥150 questions; answers **only** via `verify_by_execution`
- [ ] export `human_review_batch.json` (~20%)
- [ ] `py validate_day5.py`

## Day 6 — Validator + scorer
- [ ] pack gold as sample zip → validator PASS
- [ ] gold-vs-gold scorer answer_accuracy = 1.0
- [ ] write `stats/day6_*.json` then `py validate_day6.py`

## Day 7 — Handoff
- [ ] `docs/week1_report.md` + `status/week1_final_status.md`
- [ ] backup tar
- [ ] **STOP** — do not start Week 2
