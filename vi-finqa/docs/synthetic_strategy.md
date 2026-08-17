# Synthetic Data Strategy (Week 2 Day 1)

## Audit Week 1

- coverage: **0.9959**
- gold_n: **160**
- verified_ratio: **1.0000**
- action: `proceed_to_week2`

## Gold distribution (thật)

- n_total: 160
- verified: 160
- n_companies (from meta): 19

### By category

| category | n |
|---|---|
| simple_lookup | 50 |
| calculation | 30 |
| thuyet_minh | 30 |
| multi_table | 25 |
| company_compare | 25 |

### By year (meta)

| year | n |
|---|---|
| 2014 | 70 |
| 2015 | 45 |
| 2016 | 23 |
| 2017 | 9 |
| 2018 | 8 |
| 2019 | 1 |
| 2020 | 2 |
| 2021 | 2 |

### Top companies in gold meta

| company | n |
|---|---|
| AAA | 131 |
| ACV | 10 |
| CEO | 4 |
| DLG | 4 |
| FIT | 4 |
| GAS | 4 |
| GVR | 4 |
| HHS | 3 |
| DBC | 2 |
| DIG | 2 |
| DTK | 2 |
| HAG | 2 |
| HBC | 2 |
| IJC | 2 |
| MWG | 2 |

## Long-format coverage (source for templates)

- n_rows: 332038
- n_mapped: 46065
- n_companies: 100

### Top canonical metrics

| canonical | n |
|---|---|
| Tiền và tương đương tiền | 3218 |
| Nợ ngắn hạn | 3175 |
| Phải thu ngắn hạn | 2501 |
| Lưu chuyển tiền thuần từ HĐĐT | 2320 |
| Đầu tư tài chính ngắn hạn | 2268 |
| Hàng tồn kho | 2031 |
| Lưu chuyển tiền thuần từ HĐKD | 1988 |
| Tiền | 1861 |
| Tài sản ngắn hạn | 1669 |
| Tài sản dài hạn | 1645 |
| Chi phí khấu hao | 1640 |
| Chi phí tài chính | 1563 |
| Lợi nhuận trước thuế | 1517 |
| Thuế và các khoản phải nộp Nhà nước | 1509 |
| Nợ dài hạn | 1508 |
| Vốn chủ sở hữu | 1493 |
| Lợi nhuận sau thuế chưa phân phối | 1361 |
| Chi phí quản lý doanh nghiệp | 1147 |
| LNST | 1131 |
| Doanh thu thuần | 1014 |

## Gaps vs Week 2 taxonomy

Gold Week 1 dùng 5 category nội bộ (`simple_lookup`…). Taxonomy Week 2 có 12 loại.
Các loại **chưa** có trong gold hoặc mỏng: `ratio_structure`, `financial_index`,
`multi_year_trend`, `unit_rounding`, `negative_edge_case`.
Generator template sẽ ưu tiên các loại này trên long-mapped index.

## Generation policy

1. Template-first (không LLM) — mỗi sample verify bằng pandas trên CSV thật.
2. Rule-based paraphrase (giữ query + answer).
3. LLM optional nếu có API key (không block AC).
4. Gold set **không** dùng để train/generate thêm — chỉ few-shot wording + eval.
5. Dedup câu hỏi (token Jaccard / embedding nếu có).

## Taxonomy keys

| key | desc |
|---|---|
| `lookup_simple` | Giá trị 1 chỉ tiêu, 1 năm, 1 công ty |
| `compare_2years` | So sánh tuyệt đối/% giữa 2 năm |
| `ratio_structure` | Tỷ lệ / cơ cấu (vd TSNH/Tổng TS) |
| `financial_index` | ROE, ROA, biên lợi nhuận, vòng quay... |
| `multi_year_trend` | Xu hướng nhiều năm / CAGR |
| `multi_table` | Kết hợp CĐKT + KQKD (vd vòng quay tổng tài sản) |
| `compare_companies` | So sánh 2 công ty cùng chỉ tiêu |
| `notes_qa` | Câu hỏi thuyết minh / ghi chú |
| `unit_rounding` | Đơn vị / làm tròn / số âm |
| `negative_edge_case` | Chỉ tiêu có giá trị âm (lỗ, dòng tiền âm...) |
| `yoy_abs_diff` | Chênh lệch tuyệt đối cùng chỉ tiêu giữa 2 năm liền kề |
| `sum_two_metrics` | Tổng hai chỉ tiêu cùng công ty-năm |
