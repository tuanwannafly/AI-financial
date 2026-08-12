# Day 4 Status — PASS

## AC
- Ontology v1: `src/schema/ontology.yaml` (core CDKT / KQKD / LCTT / ratios)
- Metadata → normalize: **125,192** tables processed
- Unique terms: **157,468**
- Mapped to ontology: **2,828** (≥ threshold fuzzy/exact)
- Review queue (conf < 0.7): **144,743** → `data/processed/review_queue.jsonl` (backlog OK, not blocker)
- Long format: **332,038** rows → `data/processed/long_format.jsonl`
- Mapped long: **46,065** rows (13.9%) → `data/processed/long_format_mapped.jsonl`
- Years: 2013–2025
- `validate_day4.py` → **PASS**

## Schema (long)
```
chỉ_tiêu | năm | giá_trị | đơn_vị | report_id | start_line | table_type | company | is_consolidated
(+ canonical, confidence on mapped file)
```

## Modules
- `src/schema/ontology.yaml` — expanded seed
- `src/schema/normalize.py` — prefix strip + diacritic key + rapidfuzz
- `src/schema/longify.py` — HTML table → long; year cols only; `01/01/YYYY` → prior year
- `src/schema/run_normalize.py` — terms + longify pipeline
- `src/schema/attach_canonical.py` — join ontology onto long rows

## Sample (AAA 2015 CDKT)
| chỉ_tiêu | năm | giá_trị |
|---|---|---|
| A. TÀI SẢN NGẮN HẠN | 2015 | 1,071,561,008,455 |
| I. Tiền và các khoản tương đương tiền | 2015 | 470,061,718,120 |
| 1. Tiền | 2015 | 242,393,182,850 |

## Notes / tech debt for Week 2
- Ontology coverage intentionally starter-level; review_queue is large (detail note lines)
- Expand aliases when gold set (Day 5) surfaces missing core indicators
- Bank-form headers (Năm nay / Năm trước without year) rely on path year

## Next
Day 5 — Gold set ≥150 questions, answers only via `pandas_query` execution
