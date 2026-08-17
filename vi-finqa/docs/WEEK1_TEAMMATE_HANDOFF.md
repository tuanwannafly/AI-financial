# ViFinQA — Tài liệu handoff Tuần 1 (cho teammate)

> **Mục đích:** đọc xong tài liệu này là hiểu *dự án làm gì*, *Tuần 1 đã xong phần nào*, *code/data nằm đâu*, *chạy lại thế nào*, *giới hạn / nợ kỹ thuật*, và *Tuần 2 nên bắt đầu từ đâu*.  
> **Branch:** `plan/week-1` · **Repo:** `tuanwannafly/AI-financial` · **Thư mục gốc code:** `vi-finqa/`  
> **Trạng thái:** Week 1 **COMPLETE** — agent đã dừng, không tự bắt đầu Week 2.

---

## 1. Bối cảnh dự án (1 phút)

**ViFinQA** là benchmark QA tài chính tiếng Việt: hỏi đáp số liệu trên **Báo cáo tài chính (BCTC)** OCR của ~100 công ty niêm yết (2015–2025).

| Thành phần public (HuggingFace) | Có / Không |
|---|---|
| ~1,973 file BCTC OCR (`.txt`, nhiều bảng HTML inline) | Có |
| ~1,012 câu hỏi tiếng Việt | Có (chỉ text câu hỏi) |
| Answer / gold table CSV / pandas program | **Không** |
| 143k normalized tables (paper repo) | **Không** trong HF public |

**HF dataset dùng:** [`AIGuruTinix/ViFinQA`](https://huggingface.co/datasets/AIGuruTinix/ViFinQA)  
(duplicate của `HuuDong03uet/ViFinQA`, nhiều download hơn; nội dung tương đương)

**License OCR nguồn:** CC BY-NC 4.0 (TiniX) — dùng phi thương mại, ghi attribution.

**Mục tiêu hệ thống end-to-end (nhiều tuần):**  
câu hỏi → retrieve bảng/tài liệu liên quan → trích CSV evidence → sinh `pandas_query` → ra đáp án số → chấm F2 retrieval + answer accuracy.

**Tuần 1 chỉ làm “Data Foundation”:** tải data, extract bảng, chuẩn hóa schema/ontology, tự dựng gold seed, validator + scorer local. **Chưa** có retrieval model / text2pandas model.

---

## 2. Tuần 1 đã hoàn thành gì? (tóm tắt điều hành)

| # | Hạng mục | Kết quả |
|---|----------|---------|
| 1 | Môi trường + skeleton repo | PASS |
| 2 | Tải full dataset về local | 1,973 BCTC + 1,012 Q |
| 3 | Table extractor (HTML OCR) | Coverage **99.59%** file |
| 4 | Metadata toàn kho | **125,192** bảng |
| 5 | Long-format (chỉ_tiêu × năm × giá_trị) | **332,038** dòng |
| 6 | Ontology v1 + fuzzy normalize | 2,828 term mapped; review queue lớn |
| 7 | Gold set tự build | **160** câu, **100%** verify bằng execution |
| 8 | Submission validator | PASS 160/160 trên gold-as-submission |
| 9 | Local scorer self-check | answer=**1.0**, exec=**1.0**, F2=**1.0** |
| 10 | Report + backup + push branch | Xong |

**Định nghĩa “xong Tuần 1”** = các gate `validate_day1.py` … `validate_day7.py` + `validate_repo.py` đều PASS (khi artifact local đủ).

---

## 3. Pipeline dữ liệu (hiểu flow này là nắm 80%)

```
HuggingFace AIGuruTinix/ViFinQA
        │
        ▼
 data/raw/financial_statements/TICKER/YEAR/DOC/*_extracted.txt
 data/raw/questions/questions.jsonl          (chỉ id + question text)
 data/raw/code_stock.csv
        │
        │  Day 2–3: table_extractor (HTML <table>)
        ▼
 data/extracted/metadata.jsonl               # 1 dòng = 1 TableRecord
        │
        ├─► Day 4: longify (chỉ CDKT/KQKD/LCTT)
        │         ▼
        │   data/processed/long_format.jsonl
        │         ▼
        │   attach_canonical (ontology)
        │         ▼
        │   data/processed/long_format_mapped.jsonl
        │
        └─► Day 4: normalize terms (fuzzy)
                  ▼
            normalized_terms.jsonl + review_queue.jsonl
        │
        ▼ Day 5
 data/gold/gold_set.json
 data/gold/evidence/q_XXXX.csv               # evidence cho từng câu
 data/gold/human_review_batch.json           # 20% chờ người duyệt
        │
        ▼ Day 6
 data/gold/sample_submission.zip             # gold đóng gói như submission
 validators/*  → stats/day6_*.json
```

**Nguyên tắc cứng (quan trọng):**  
Số trong gold **không** do LLM bịa. Chỉ được ghi `answer` sau khi `eval(pandas_query)` trên CSV evidence thành công (`verified_by_execution: true`).

---

## 4. Cấu trúc thư mục `vi-finqa/`

```
vi-finqa/
├── README.md
├── requirements.txt
├── .gitignore                 # raw/extracted/processed/jsonl lớn KHÔNG commit
├── validate_repo.py           # gate bootstrap
├── validate_day1.py … day7.py # gate từng ngày
│
├── src/
│   ├── utils/                 # download HF, sample explore, logging
│   ├── extraction/            # table extractor, full run, report, refine
│   ├── schema/                # ontology, normalize, longify, attach canonical
│   ├── gold/                  # build gold set + helpers
│   ├── retrieval/             # (placeholder — Week 2)
│   └── text2pandas/           # (placeholder — Week 2)
│
├── validators/
│   ├── submission_validator.py
│   ├── local_scorer.py
│   └── day6_selfcheck.py      # pack gold zip + self-check
│
├── data/
│   ├── raw/                   # HF dump (local only, ~380MB+)
│   ├── extracted/             # metadata.jsonl (local only, ~300MB)
│   ├── processed/             # long_format*, review_queue (local only)
│   └── gold/                  # gold_set.json (IN git) + evidence/ (local)
│
├── docs/
│   ├── WEEK1_TEAMMATE_HANDOFF.md   # ← file này
│   ├── week1_report.md             # số liệu + fail cases + synthetic strategy
│   ├── week1_agent_checklist.md
│   └── ESCALATION_TEMPLATE.md
│
├── status/                    # day0…day7 + week1_final_status.md
├── stats/                     # JSON metrics (nhẹ, có trong git)
├── notes/data_exploration.md
├── scripts/                   # smoke test, backup
├── logs/ , checkpoints/ , backups/   # runtime (gitignore)
```

### Cái gì **có** trên GitHub vs **chỉ local**

| Có trên branch `plan/week-1` | Chỉ máy local (gitignore / không push) |
|---|---|
| Toàn bộ `src/`, `validators/`, `validate_*.py` | `data/raw/` (HF) |
| `data/gold/gold_set.json`, `human_review_batch.json` | `data/extracted/metadata.jsonl` (~303 MB) |
| `docs/`, `status/`, `stats/`, `notes/` | `data/processed/*.jsonl` |
| `requirements.txt`, `.gitignore` | `data/gold/evidence/*.csv` |
| | `data/gold/sample_submission.zip` |
| | `backups/`, `logs/`, `checkpoints/` |

> **Lý do:** GitHub chặn file >100 MB. Lần push đầu fail vì `metadata.jsonl`. Đã rewrite commit: code + gold JSON nhẹ; artifact nặng regenerate local.

---

## 5. Schema quan trọng (đọc khi code)

### 5.1 `TableRecord` (mỗi dòng `metadata.jsonl`)

| Field | Ý nghĩa |
|---|---|
| `report_id` | stem file, vd `AAA_financial_statements_2015_consolidated_extracted` |
| `start_line` / `end_line` | 0-based trong file raw |
| `table_type` | `CDKT` \| `KQKD` \| `LCTT` \| `THUYET_MINH` \| `UNKNOWN` |
| `unit` | vd `Đơn vị: VND` (thường sparse) |
| `company` | ticker từ path (`AAA`, `VCB`, …) |
| `year` | năm từ path |
| `is_consolidated` | true/false từ `consolidated`/`separate` trong tên file |
| `raw_text` | HTML table (có truncate) |
| `rows` | `list[list[str]]` — cells đã parse |
| `source` | `html` hoặc `plain` |

**Phát hiện then chốt Day 1–2:** BCTC OCR gần như **toàn HTML** (`<table><tr><td>…`), không phải plain text cột cách khoảng trắng. Extractor heuristic thuần regex header **không đủ** → đã viết parser HTML.

### 5.2 Long format (`long_format.jsonl`)

```
chỉ_tiêu | năm | giá_trị | đơn_vị | report_id | start_line | table_type | company | is_consolidated
```

- Chỉ longify **MAIN** types: CDKT / KQKD / LCTT (chưa longify THUYET_MINH).
- Cột năm detect từ header: `31/12/2015`, `Năm 2015`, `Năm nay`/`Năm trước`, …
- `01/01/YYYY` (số đầu năm) → map **năm trước** (opening balance).
- **Chỉ emit cột có year mapping** — tránh nhầm cột “Mã số” thành giá_trị.

`long_format_mapped.jsonl` = long + `canonical` + `confidence` (nếu match ontology).

### 5.3 Ontology (`src/schema/ontology.yaml`)

Canonical metrics lõi (ví dụ): Doanh thu thuần, LNST, TSNH/TSDH, Tổng tài sản, Nợ NH/DH, VCSH, Tiền & TĐT, Hàng tồn kho, Chi phí TC/QLDN, Lưu chuyển HĐKD, EPS/ROE/ROA, …

Normalize: strip prefix `1. `/`I. `, bỏ dấu để match, rapidfuzz `token_sort_ratio`, threshold ~85.  
Conf &lt; 0.7 → `review_queue.jsonl` (**không block pipeline** — backlog người/Week 2).

### 5.4 Gold question (mỗi phần tử trong `gold_set.json`)

```json
{
  "question_id": "q_0001",
  "question": "Chi phí bán hàng của AAA năm 2014 (BCTC hợp nhất) là bao nhiêu VND?",
  "category": "simple_lookup",
  "relevant_docs": ["AAA_financial_statements_2015_consolidated_extracted"],
  "relevant_tables": ["AAA_..._extracted|277"],
  "evidence_csv": "data/gold/evidence/q_0001.csv",
  "csv_path": "data/gold/evidence/q_0001.csv",
  "pandas_query": "df[(df['canonical']=='Chi phí bán hàng') & ...]['giá_trị'].iloc[0]",
  "answer": 78937784265.0,
  "unit": "VND",
  "verified_by_execution": true
}
```

**5 category (đều có mặt):**

| Category | Ý nghĩa | ~số câu |
|---|---|---|
| `simple_lookup` | 1 chỉ tiêu 1 công ty 1 năm | 50 |
| `calculation` | YoY diff cùng metric | 30 |
| `multi_table` | cộng/trừ 2 metric cùng co-year | 25 |
| `company_compare` | cùng metric 2 công ty 1 năm | 25 |
| `thuyet_minh` | proxy note metrics (khấu hao, thuế, …) | 30 |

> `thuyet_minh` hiện là **proxy** (metric chi tiết từ main tables), chưa phải longify từ HTML THUYẾT MINH thật — ghi nợ Week 2.

### 5.5 Submission format (validator)

Zip phải chứa:

- `submission.json`: list object với keys  
  `question_id`, `relevant_tables`, `csv_path`, `pandas_query`, `answer`
- Các file CSV đúng path `data/...` nằm **trong zip**
- `relevant_tables[]` format `report_id|line`

Scorer:

- **Table retrieval:** macro F2 (β=2, ưu tiên recall)
- **Execution accuracy:** `pandas_query` chạy được
- **Answer accuracy:** so số với gold (abs_tol=1.0 hoặc rel_tol=0.1%)

---

## 6. Module code — ai làm việc gì

| Module | File chính | Việc |
|---|---|---|
| Download | `src/utils/download.py`, `download_cli.py` | `snapshot_download` HF → `data/raw` |
| Explore | `src/utils/run_day1_explore.py`, `sample_explore.py` | sample 25 file → `notes/data_exploration.md` |
| Extract | `src/extraction/table_extractor.py` | HTML table → TableRecord |
| Coverage test | `src/extraction/test_coverage.py` | n=50 sample coverage |
| Full run | `src/extraction/run_full.py` | parallel + checkpoint `checkpoints/day3.json` |
| Report extract | `src/extraction/build_extraction_report.py` | → `stats/extraction_report.json` |
| Refine | `heuristic_refine.py`, `llm_refine.py` | heuristic; LLM optional nếu có `ANTHROPIC_API_KEY` |
| Ontology | `src/schema/ontology.yaml` | seed chỉ tiêu |
| Normalize | `src/schema/normalize.py`, `run_normalize.py` | term → canonical |
| Longify | `src/schema/longify.py` | TableRecord → long rows |
| Canonical join | `src/schema/attach_canonical.py` | long + term map |
| Gold | `src/gold/build_gold_set.py` | sinh + verify execution |
| Validate submission | `validators/submission_validator.py` | zip schema |
| Score | `validators/local_scorer.py` | F2 + answer + exec |
| Day6 pack | `validators/day6_selfcheck.py` | gold → zip → validate → score |

---

## 7. Setup máy mới (Windows — máy này dùng `py`, không phải `python`)

```powershell
cd "C:\work\AI financial\vi-finqa"
py -m pip install -r requirements.txt
$env:PYTHONIOENCODING = "utf-8"   # tránh lỗi console cp1252 với tiếng Việt

py validate_repo.py
```

### Tải raw data (bắt buộc nếu chưa có `data/raw/`)

```powershell
py -m src.utils.download_cli --repo_id AIGuruTinix/ViFinQA --local_dir data/raw
```

### Chạy lại full pipeline (nếu cần regenerate artifact lớn)

```powershell
# Day 2 sample coverage
py -m src.extraction.test_coverage data/raw --n 50 --out stats/day2_coverage.json
py validate_day2.py

# Day 3 full extract (~40s với 6 jobs trên máy dev)
py -m src.extraction.run_full data/raw --jobs 6 --batch-size 50 --reset
py -m src.extraction.build_extraction_report
py validate_day3.py

# Day 4
py -m src.schema.run_normalize
py -m src.schema.attach_canonical
py validate_day4.py

# Day 5
py -m src.gold.build_gold_set --min_n 150
py validate_day5.py

# Day 6
py -m validators.day6_selfcheck
py validate_day6.py
```

Smoke extractor (synthetic BCTC, không cần HF):

```powershell
py scripts/smoke_test_extractor.py
```

---

## 8. Cách đọc raw file thật (để khỏi “shock” OCR)

Ví dụ path:

```
data/raw/financial_statements/AAA/2015/AAA_financial_statements_2015_consolidated/
  AAA_financial_statements_2015_consolidated_extracted.txt
```

Trong file:

- Marker trang: `===== PAGE N =====`
- Bảng: cả dòng HTML một dòng dài  
  `<table><tr><td>TÀI SẢN</td><td>Mã số</td>…</tr>…</table>`
- Header statement plain text gần bảng:  
  `BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT`, `KẾT QUẢ HOẠT ĐỘNG KINH DOANH`, …
- Tên file: `consolidated` / `separate` / `aggregated` / đôi khi `explanatory`

**Không** expect layout “cột căn đều bằng space” như FinQA English PDF clean.

---

## 9. Số liệu chi tiết (single source: `docs/week1_report.md`)

| Metric | Giá trị |
|---|---|
| Files BCTC | 1,973 |
| Files có ≥1 bảng | 1,965 (99.59%) |
| Files empty | 8 (toàn PRT letter/explanation) |
| Bảng extracted | 125,192 |
| CDKT / KQKD / LCTT | 8,875 / 9,175 / 4,254 |
| THUYET_MINH / UNKNOWN | 74,354 / 28,534 |
| Long rows | 332,038 |
| Unique terms | 157,468 |
| Mapped terms | 2,828 |
| Review queue | 144,743 |
| Gold | 160 (32 human batch) |
| Scorer self-check | 1.0 / 1.0 / 1.0 |

---

## 10. Giới hạn & nợ kỹ thuật (đọc trước khi sửa)

1. **Ontology coverage thấp** trên unique terms — đa số là dòng thuyết minh chi tiết / header section; review_queue là backlog có chủ đích, không fail Day 4.
2. **Bank/TCTD forms** (BID, CTG, VCB, …) nhiều UNKNOWN — cần pattern riêng.
3. **Longify chưa cover THUYET_MINH** HTML notes.
4. **Unit sparse** — scorer/gold đang chủ yếu VND raw; chưa chuẩn hóa triệu/tỷ thống nhất.
5. **Gold là synthetic từ long rows**, không phải official ViFinQA labels (HF không public answer).
6. **Human review 32 câu** chưa duyệt tay — nên review trước khi tin gold cho paper.
7. **`retrieval/` và `text2pandas/` trống** — đúng scope Tuần 1.
8. **Public questions.jsonl** (1,012 câu) **chưa** map vào gold Week 1 — gold tự gen từ metrics; Tuần 2 có thể align với official questions nếu có annotation riêng.
9. Console Windows: luôn set `PYTHONIOENCODING=utf-8`.
10. Không commit raw/extracted/processed — disk local hoặc backup `backups/week1_*.tar.gz`.

Chi tiết fail cases 50 mục: xem `docs/week1_report.md`.

---

## 11. Quy ước vận hành agent / team (từ plan)

- Mỗi “ngày” = 1 module + `validate_dayN.py` đo được.
- Status ghi `status/day{N}_status.md` — người đọc bất cứ lúc nào, không cần agent hỏi.
- Escalate (dừng, không đoán) khi: coverage kẹt sau 3 retry, ontology mâu thuẫn công thức, gold query fail 2 lần, data thiếu >5%, LLM JSON hỏng >5%.
- Template escalate: `docs/ESCALATION_TEMPLATE.md`.
- **Tuần 1 đã đóng** — không auto sang Tuần 2.

---

## 12. Gợi ý Tuần 2 (cho teammate lead)

Thứ tự đề xuất (có thể đổi theo ưu tiên product):

### A. Chất lượng data (nền)
1. Human-review 32 gold batch → fix evidence sai.
2. Mở rộng ontology từ top frequency `review_queue` + bank terms.
3. Longify THUYET_MINH + unit normalizer.

### B. Retrieval
4. Index `report_id|start_line` + text/rows (BM25 / dense).
5. Train/eval table retrieval với F2 trên gold `relevant_tables`.

### C. Text2Pandas / answering
6. Model/prompt sinh `pandas_query` từ (question + evidence CSV).
7. End-to-end: retrieve → CSV → query → answer; chấm bằng `local_scorer`.

### D. Synthetic data
8. Paraphrase câu gold (giữ answer + CSV).
9. Compositional ops (%, multi-year) — **mọi synthetic phải re-verify execution**.
10. Hard negatives cho retrieval.

Chiến lược synthetic chi tiết: cuối `docs/week1_report.md`.

---

## 13. Checklist onboarding teammate (30–60 phút)

- [ ] Clone branch `plan/week-1`, mở `vi-finqa/`
- [ ] Đọc **file này** + lướt `docs/week1_report.md`
- [ ] `py -m pip install -r requirements.txt` + `py validate_repo.py`
- [ ] Nếu chưa có data: download HF (~vài phút–chục phút tùy mạng)
- [ ] Mở 1 raw file (vd AAA 2015 consolidated) — nhìn HTML table
- [ ] Đọc 3–5 câu trong `data/gold/gold_set.json` + file evidence CSV tương ứng
- [ ] Chạy `py -m validators.day6_selfcheck` (cần evidence local; nếu thiếu thì `build_gold_set` lại)
- [ ] Đọc `src/extraction/table_extractor.py` (extract) + `src/schema/longify.py` (long)
- [ ] Ghi note: phần mình nhận (retrieval / ontology / gold QA / …)

---

## 14. Lệnh “sự thật” nhanh (health check)

```powershell
cd vi-finqa
$env:PYTHONIOENCODING='utf-8'

# Có raw?
(Get-ChildItem data\raw -Recurse -Filter *.txt | Measure-Object).Count
# expect ~1973 (+ smoke)

# Có metadata?
Test-Path data\extracted\metadata.jsonl

# Gold có trong git
(Get-Item data\gold\gold_set.json).Length

# Gates (artifact local đủ mới PASS hết)
py validate_day5.py   # gold JSON đủ là PASS
py validate_day7.py   # report + backup local
```

---

## 15. Liên hệ tài liệu & PR

| Tài liệu | Path |
|---|---|
| Handoff teammate (bản này) | `docs/WEEK1_TEAMMATE_HANDOFF.md` |
| Report số liệu + fail + synthetic | `docs/week1_report.md` |
| Checklist agent | `docs/week1_agent_checklist.md` |
| Final status | `status/week1_final_status.md` |
| Day status | `status/day0_…_day7_status.md` |
| Stats JSON | `stats/*.json` |
| Tạo PR | https://github.com/tuanwannafly/AI-financial/pull/new/plan/week-1 |

**Code companion paper (tham khảo, layout khác public HF):**  
https://github.com/DSKT-NOWJ/ViFinQA

---

## 16. Tóm tắt một câu cho standup

> Tuần 1 xong data foundation: extract 99.6% BCTC HTML → 125k bảng → 332k long rows → gold 160 câu verify-by-execution → validator/scorer self-check 1.0; artifact nặng local-only; branch `plan/week-1` đã push; Week 2 = retrieval + text2pandas + ontology/gold polish.

---

*Tài liệu soạn sau khi đóng Week 1 (2026-08-12). Nếu conflict với code, ưu tiên code + `validate_dayN.py` output.*
