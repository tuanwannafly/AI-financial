# Day 3 Status — PASS

## AC
- Full corpus run: **1973** report files
- Coverage: **99.59%** (1965/1973) ≥ 90%
- Main-statement file coverage: **99.49%**
- `validate_day3.py` → **PASS**
- Checkpoint: `checkpoints/day3.json` (1973 done)
- Metadata: `data/extracted/metadata.jsonl` (~318 MB, 125,192 tables)

## Run
```
py -m src.extraction.run_full data/raw --jobs 6 --batch-size 50 --reset
# elapsed ~42s
```

## Stats (`stats/extraction_report.json`)
| metric | value |
|---|---|
| n_tables | 125,192 |
| CDKT | 8,875 |
| KQKD | 9,175 |
| LCTT | 4,254 |
| THUYET_MINH | 74,354 |
| UNKNOWN | 28,534 |
| companies | 100 |
| tables/file p50 | 60 |

## Empty files (8) — expected non-statement docs
All `PRT_*` explanatory letters / explanations (no numeric HTML tables). Listed in `stats/day3_empty_files.json`. **Not escalated** (coverage well above 90%).

## LLM-assist
- Heuristic refine ran (0 relabel — content typing already applied at extract time)
- Anthropic path available if `ANTHROPIC_API_KEY` set; not required for AC

## Schema sample
`report_id, start_line, end_line, table_type, unit, company, year, is_consolidated, raw_text, rows, source`

## Next
Day 4: ontology expand + `run_normalize` → `review_queue.jsonl`
