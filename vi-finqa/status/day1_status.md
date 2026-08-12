# Day 1 Status — PASS

## Download
- repo_id: `AIGuruTinix/ViFinQA`
- path: `data/raw/`
- n_txt: **1974** (1973 real + 1 smoke)
- questions: `data/raw/questions/questions.jsonl` (1,012)
- code_stock: `data/raw/code_stock.csv`
- structure: `financial_statements/TICKER/YEAR/DOC/*_extracted.txt`

## Explore
- `notes/data_exploration.md`: 25 file blocks
- OCR issue lines: 25
- `validate_day1.py`: **PASS**

## Patterns observed (critical for Day 2)
- **All sampled files use inline HTML tables** (`<table><tr><td>...`)
- Page markers: `===== PAGE N =====`
- KQKD / LCTT / THUYẾT MINH markers present in sample
- CDKT header text may be OCR-variant / English / missing plain text — extractor must parse **HTML tables**, not only Vietnamese header regex
- Reports: consolidated / separate / aggregated in filename
- No gold answers in public release — gold set is self-built (Day 5)

## Next
Day 2: rewrite/extend `table_extractor.py` for HTML tables + tune header patterns on real samples.
