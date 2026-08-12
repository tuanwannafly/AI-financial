# Day 6 Status — PASS

## AC
- Sample zip from gold: `data/gold/sample_submission.zip` (160 items + evidence CSVs)
- `submission_validator` on gold-as-submission → **PASS 160/160**
- `local_scorer` gold-vs-gold:
  - macro_f2 = **1.0**
  - answer_accuracy = **1.0**
  - execution_accuracy = **1.0**
- `validate_day6.py` → **PASS**

## Artifacts
- `stats/day6_validator.json`
- `stats/day6_scorer.json`
- `validators/day6_selfcheck.py` (pack + validate + score)
- `validators/submission_validator.py`
- `validators/local_scorer.py`

## Self-check meaning
Gold used as both prediction and reference proves scorer logic + evidence CSVs + pandas_query are consistent before real model eval.

## Next
Day 7 — week1 report, fail-case review, backup, stop before Week 2.
