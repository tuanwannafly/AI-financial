# Day 2 Status — PASS

## AC
- Sample: 50 real files (exclude `_smoke`)
- Coverage: **1.00** (50/50) ≥ 0.70
- `stats/day2_coverage.json`
- `validate_day2.py` → PASS
- Smoke: 4 types CDKT/KQKD/LCTT/THUYET_MINH

## Extractor changes (`src/extraction/table_extractor.py`)
1. **HTML primary path** — parse every `<table>…</table>` via `html.parser`
2. Skip TOC tables (`TRANG` / page index)
3. Statement headers OCR-tolerant: CDKT / KQKD / LCTT / THUYẾT MINH
4. Content-based type inference when header missing/wrong
5. Metadata from path: `company`, `year`, `is_consolidated`
6. Unit: `Đơn vị: VND|triệu|tỷ|…`
7. Plain-text fallback for non-HTML smoke samples

## Type mix (seed 42, n=50)
See `stats/day2_coverage.json` → `by_table_type`  
Main statements present on almost all files; many note tables labeled THUYET_MINH/UNKNOWN (expected).

## Known limits (Day 3)
- Sticky/mislabel: some note tables still typed CDKT via content heuristics
- Header OCR variants still incomplete for banks (TCTD forms)
- No LLM-assist yet

## Next
Day 3: full corpus `run_full.py` + `build_extraction_report.py` + LLM refine low-confidence → coverage ≥ 0.90
