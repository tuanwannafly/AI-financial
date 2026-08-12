# Day 5 Status — PASS

## AC
- Gold set: **160** ≥ 150
- `verified_by_execution: true` on **100%**
- Categories (5/5):
  - simple_lookup: 50
  - calculation: 30
  - multi_table: 25
  - company_compare: 25
  - thuyet_minh: 30
- Human review batch: **32** (20%) → `data/gold/human_review_batch.json`
- `validate_day5.py` → **PASS**

## Rule enforced
Answers come **only** from `eval(pandas_query)` on evidence CSV — never LLM-invented numbers.

## Artifacts
- `data/gold/gold_set.json`
- `data/gold/evidence/q_XXXX.csv` (one per question)
- `data/gold/human_review_batch.json`
- Builder: `src/gold/build_gold_set.py`

## Schema sample
```json
{
  "question_id": "q_0001",
  "question": "...",
  "category": "simple_lookup",
  "relevant_docs": ["..."],
  "relevant_tables": ["report_id|start_line"],
  "evidence_csv": "data/gold/evidence/q_0001.csv",
  "pandas_query": "df[...]",
  "answer": <float from execution>,
  "unit": "VND",
  "verified_by_execution": true
}
```

## Notes
- `thuyet_minh` uses note-proxy metrics (khấu hao, thuế, chi phí nhân công…) because longify currently emits main statements only.
- Human review batch is for parallel human QA — does **not** block Day 6.

## Next
Day 6 — `submission_validator` + `local_scorer` self-check on gold.
