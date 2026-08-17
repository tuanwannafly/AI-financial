# Week 4 Priority (ROI — số liệu thật)

## Audit W3
- `e2e_eval.json` ban đầu **không tồn tại** → vá tối thiểu (template E2E, không LLM) rồi đo baseline.
- Baseline E2E (trước Day 2 improve): ok **46.25%**, answer_acc **53.1%**, retrieval_miss **19.4%**, generation_wrong_logic **33.1%**

## ROI ranking (n=160)

| category | count | potential gain |
|---|---|---|
| generation_wrong_logic | 53 | **33.1%** |
| retrieval_miss | 31 | **19.4%** |
| unit_mismatch | 2 | 1.3% |
| execution_fail_unrepaired | 0 | 0% |

## Cross-tab (gold cat × error)
- calculation × generation_wrong_logic: 28
- multi_table × generation_wrong_logic: 25
- company_compare × retrieval_miss: 14
- thuyet_minh × retrieval_miss: 12

## Targets chọn (impact ≥5%)
1. **generation_wrong_logic** → template YoY / sum-diff / ticker pair `(AAA − ACV)`
2. **retrieval_miss** → QU intent + expand (partial; F2 vẫn thấp vì top-k table keys)
3. **unit_mismatch** — dưới 5%, chỉ postprocess nhẹ

**Không chọn:** harden repair (exec đã 100% oracle / 94% E2E, delta repair = 0).

## Day 2 after
- ok **72.5%** (+26.25 pp)
- answer_acc **86.25%**
- generation_wrong_logic **8.1%**
- retrieval_miss không đổi 19.4% (không có dense; không vá lớn tuần cuối)

## notes_qa
- gold `thuyet_minh` = **30/30 numeric** → không escalate text-QA.
