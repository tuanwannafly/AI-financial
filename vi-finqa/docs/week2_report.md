# Week 2 Report

## Audit Week 1
- coverage **99.59%**, gold **160**, verified_ratio **1.0** → `proceed_to_week2`

## Synthetic data
- Tổng verified (sau dedup): **6,739** (train 6,066 + holdout 673) ≥ 5,000
- Pass rate generation: **~100%** (template + sandbox/inline verify; chỉ giữ `verified=true`)
- Duplicate rate sau Jaccard 0.92: **~0%** (paraphrase đủ khác)
- Phân bố category (full 6739):

| category | n | % |
|---|---|---|
| lookup_simple | 900 | 13.4 |
| notes_qa | 900 | 13.4 |
| negative_edge_case | 900 | 13.4 |
| sum_two_metrics | 728 | 10.8 |
| ratio_structure | 459 | 6.8 |
| compare_2years | 450 | 6.7 |
| yoy_abs_diff | 450 | 6.7 |
| multi_year_trend | 450 | 6.7 |
| unit_rounding | 450 | 6.7 |
| multi_table | 436 | 6.5 |
| financial_index | 376 | 5.6 |
| compare_companies | 240 | 3.6 |

- `compare_companies` **<5%** sau top-up: giới hạn số cặp (year, metric) trong long-mapped — không escalate thêm (bản chất data).
- Không LLM key trên máy → **template-first**, không gọi Anthropic/OpenAI.
- Pilot review (chất lượng câu): `data/synthetic/pilot_review_batch.json` (80) — song song, không block.
- Gold **không** dùng để generate thêm.

## Retrieval
- Index: BM25 metric-level `data/retrieval_index/bm25_metric.pkl` (80k docs, cắt trần)
- Dense/FAISS/`bge-m3`: **chưa** (không cài GPU/model nặng trong tuần; hook sẵn trong `HybridRetriever`)
- Gold table keys **211/211** có trong corpus table-level
- Sau representation + QU (diacritic alias) + company filter:

| metric | value |
|---|---|
| nonempty_rate | 0.944 |
| Recall@5 | **0.672** |
| Recall@10 | **0.725** |
| Recall@20 | **0.812** |
| lookup R@10 | 0.733 |
| compare_years R@10 | 0.833 |
| compare_companies R@10 | 0.375 |

- Recall@20 **81.3%** ≥ 70% (không escalate). Mục tiêu 85% chưa chạm — nợ dense + full 332k metric docs.

## Error analysis (draft E2E top-1 + template pandas)
- `retrieval_fail_rate` top-1: **75.6%** — kỳ vọng: hệ tối ưu **Recall@20/F2**, không top-1
- generation_fail (khi top-1 đúng): 11.3%
- exact answer ok_rate top-1: 13.1%
- Breakdown files: `stats/error_breakdown_before.json` (after = same; chưa hard-neg LLM)

## Query understanding
- NER: year regex + ticker substring + ontology `key_of` (bỏ dấu)
- Intent: lookup / compare_years / compare_companies / ratio / index / trend
- Test thủ công: câu AAA 2014 extract year+ticker; “Chi phí bán hàng” map canonical sau fix diacritics

## Rủi ro / nợ kỹ thuật mang sang Tuần 3
1. Dense retriever (bge-m3 + FAISS) chưa chạy — BM25-only
2. Metric index cắt 80k / 332k long rows
3. `compare_companies` synthetic + retrieval yếu
4. E2E text2pandas mới là template 1-metric; multi-hop/YoY chưa
5. Hard-negative mining chưa scale (không LLM)
6. Sandbox `spawn` chậm nếu dùng cho 6k (đã dùng `execute_inline` cho template tin cậy)
7. Human review 80 synthetic + 32 gold batch vẫn pending
8. Company filter miss khi ticker không xuất hiện đúng dạng trong câu

## Đề xuất Tuần 3: Text-to-Pandas + Self-Repair Loop
1. Few-shot + schema-constrained pandas từ top-k tables (không chỉ top-1)
2. Self-repair: nếu sandbox error → đơn giản hóa query / đổi bảng trong top-20
3. Bật dense index nếu có disk/RAM
4. Chấm `local_scorer` end-to-end trên gold + synthetic holdout
5. Không đụng gold để train

## Quyết định đã ghi
- Generator: template, không LLM (no API key)
- Verify: inline pandas, same SAFE_BUILTINS
- Dedup: token Jaccard 0.92
- Retriever v2: per-metric BM25, company filter, no hard year filter
- Stop: không tự mở Tuần 3
