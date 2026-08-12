# Week 1 Report

## Số liệu

| Metric | Value |
|---|---|
| Coverage extraction | **99.59%** (1965/1973 files) |
| Main-statement file coverage | **99.49%** |
| Số bảng extracted | **125,192** |
| By type | CDKT 8,875 · KQKD 9,175 · LCTT 4,254 · THUYET_MINH 74,354 · UNKNOWN 28,534 |
| Companies | 100 |
| Tables/file (p50 / mean / max) | 60 / 63.7 / 226 |
| Long-format rows | **332,038** (years 2013–2025) |
| Ontology unique terms | 157,468 |
| Terms mapped (canonical) | 2,828 |
| Long rows with canonical | 46,065 (13.9%) |
| Review queue (conf &lt; 0.7) | 144,743 |
| Gold set | **160** câu, **32/160** human review batch |
| All gold verified_by_execution | **160/160** |
| Validator (gold-as-submission) | **PASS 160/160** |
| Scorer self-check | answer_accuracy = **1.0**, execution_accuracy = **1.0**, macro_f2 = **1.0** |
| Day1–6 gates | all PASS |

## Pipeline summary

| Day | Module | Result |
|-----|--------|--------|
| 0 | Bootstrap | PASS (`validate_repo`) |
| 1 | Explore + download `AIGuruTinix/ViFinQA` | PASS (1973 txt + 1012 Q) |
| 2 | Heuristic HTML table extractor | PASS (coverage 1.0 on n=50) |
| 3 | Full corpus + checkpoint | PASS (coverage 99.59%) |
| 4 | Ontology + longify + normalize | PASS |
| 5 | Gold set (exec-only answers) | PASS (160) |
| 6 | Validator + local scorer | PASS (self-check 1.0) |
| 7 | Report + backup | this doc |

## Fail cases đáng chú ý (top / representative)

### A. Extraction empty (8 files — all PRT explanatory docs)
1. `PRT_2020_financial_statement_explanations_extracted`
2. `PRT_2021_explanatory_letters_1_extracted`
3. `PRT_2021_explanatory_letters_2_extracted`
4. `PRT_2022_explanatory_letters_1_extracted`
5. `PRT_2022_explanatory_letters_2_extracted`
6. `PRT_2023_explanatory_letters_1_extracted`
7. `PRT_2023_explanatory_letters_2_extracted`
8. `PRT_2025_financial_statement_explanations_1_extracted`

**Nguyên nhân:** không phải BCTC số liệu HTML đầy đủ; letter/explanation narrative → 0 table financial. **Không escalate** (coverage vẫn ≫ 90%).

### B. High UNKNOWN table density (sample reports)
9. `ASM_financial_statements_2024_consolidated_extracted` — 98 UNKNOWN (early sample window)
10. `ASM_financial_statements_2024_separate_extracted` — 89 UNKNOWN
11. `BID_financial_statements_2016_consolidated_extracted` — 69 UNKNOWN
12. `BID_financial_statements_2016_separate_extracted` — 65 UNKNOWN
13. `BID_financial_statements_2017_separate_extracted` — 63 UNKNOWN

**Nguyên nhân:** bank/TCTD forms + OCR header variants; content heuristics miss; sticky note tables.

### C. Ontology / normalize low-confidence (review_queue samples)
14. `1. Đầu tư nắm giữ đến ngày đáo hạn` (conf≈0.62) — missing alias HTM
15. `5. Tài sản thiếu chờ xử lý` (≈0.63)
16. `2. Thuế GTGT được khấu trừ` (≈0.65)
17. `- Nguyên giá` (≈0.57) — sub-line of PPE note
18. `- Giá trị hao mòn luỹ kế` (≈0.65)
19. `. Đầu tư vào công ty liên doanh, liên kết` (≈0.63)
20. `. Chi phí trả trước dài hạn` (≈0.67)
21. `NGUỒN VỐN` (≈0.60) — section header, not metric

### D. Structural / pipeline limits observed
22. OCR inline HTML only — plain regex headers insufficient (fixed Day 2)
23. Column “Mã số / Thuyết minh” mistaken as values if year map loose (fixed Day 4 longify)
24. `01/01/YYYY` opening balance = prior year (handled)
25. Unit sparsely captured (`n_with_unit` 2,388 / 125k tables)
26. Longify only MAIN types (CDKT/KQKD/LCTT) — note tables not longified
27. Gold `thuyet_minh` uses note-proxy metrics (not true THUYET_MINH HTML long rows)
28. Public HF release has **no gold answers** — self-built gold only
29. Fuzzy ontology map rate low on unique terms (detail lines dominate review queue)
30. Bank “Năm nay / Năm trước” depends on path year
31. Multi-company same metric year may mix consolidated vs separate if not filtered hard
32. Large metadata.jsonl (~318 MB) / long_format (~87 MB) — I/O heavy for Week 2
33. Sticky header type CDKT on later note tables (partially mitigated)
34. TOC tables filtered but residual address/letterhead tables may remain as UNKNOWN
35. Diacritic OCR noise (`CHÍ TIÊU` vs `CHỈ TIÊU`, `LƯU CHUYÊN`)
36. Negative numbers `(123)` vs `-123` — normalize_number handles common forms
37. Checkpoint path keys relative — resume-safe Day 3
38. No Anthropic LLM refine run (heuristic only; key optional)
39. Gold questions synthetic from long rows — human batch 32 still pending review
40. Submission zip self-check only — not real model predictions yet

### E. Additional edge observations (41–50)
41. Consolidated vs separate both present — gold should tag `is_consolidated`
42. Some years appear as 2013 from opening-balance shift on 2014 reports
43. Duplicate report stems across companies unlikely (stem unique enough for gold refs)
44. `relevant_tables` format `id|line` validated Day 6
45. Human review batch exported but **not** blocking Day 6/7
46. Requirements install via `py` (not `python`) on this Windows host
47. Console cp1252 Unicode issues — use `PYTHONIOENCODING=utf-8`
48. Dataset license CC BY-NC 4.0 (TiniX OCR source) — non-commercial
49. Companion repo expects richer `ocr_filter/` layout — not in public HF dump
50. Week 2 needs synthetic data strategy beyond 160 gold seed

## Rủi ro / nợ kỹ thuật mang sang Tuần 2

1. **Ontology coverage** — review_queue 144k; expand aliases from gold fail + frequency mining.
2. **Bank/TCTD extractors** — specialized patterns for ACB/BID/CTG/VCB forms.
3. **True note longify** — extend longify beyond MAIN_TYPES for THUYET_MINH tables.
4. **Unit normalization** — map VND / triệu / tỷ consistently into scorer.
5. **Gold quality** — human-review 32 items; fix any wrong evidence joins.
6. **Retrieval pipeline** not built yet (Week 2: retrieval + text2pandas).
7. **LLM refine** unused — optional for UNKNOWN re-label if budget allows.
8. **Scale** — full re-score and RAG indexing over 125k tables needs batching.

## Đề xuất synthetic data strategy cho Tuần 2

1. **Template expansion from gold:** for each verified `(company, year, canonical)` triple, generate paraphrases (Vietnamese question variants) keeping same evidence CSV + answer.
2. **Compositional ops:** YoY %, ratios (ROE/ROA if both sides exist), multi-year chains.
3. **Hard negatives:** wrong company / wrong year / wrong consolidated flag for retrieval training.
4. **Bank-specific templates:** loan book, customer deposits, provision lines once ontology grows.
5. **Noise injection (train only):** OCR-like term variants for robust normalize; never for gold answers.
6. **Hold-out:** keep human_review_batch + 20% gold as eval; rest + synthetics for train.
7. **Answer integrity:** every synthetic must re-pass `verify_by_execution` before inclusion.

## Definition of Done checklist

- [x] Repo + env + requirements
- [x] Dataset downloaded + exploration notes
- [x] Extractor coverage ≥ 90% (99.59%)
- [x] `metadata.jsonl` TableRecord schema
- [x] Ontology v1 + normalize + review_queue
- [x] Gold ≥ 150, execution-verified
- [x] submission_validator PASS on gold pack
- [x] local_scorer self-check answer_accuracy = 1.0
- [x] `docs/week1_report.md` + fail review
- [ ] Human review of 32-batch (async, non-blocking)

## Stop rule

Agent **stops after Week 1 final status**. Does **not** start Week 2 without human direction.
