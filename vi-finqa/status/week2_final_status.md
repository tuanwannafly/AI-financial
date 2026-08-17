# Week 2 Final Status — COMPLETE

**Agent STOP.** Không bắt đầu Week 3 nếu chưa có quyết định người.

## Gates
| Day | Result |
|-----|--------|
| Audit W1 | PASS → proceed |
| 1 Taxonomy + strategy | PASS (12 keys, real gold stats) |
| 2–3 Synthetic | **6,739** verified, holdout 10% |
| 4–5 Retrieval BM25 | Recall@20 **81.3%** |
| 6 E2E draft | baseline thô; top-1 yếu / R@20 ổn |
| 7 Report + backup | this + `docs/week2_report.md` |

## Artifacts
- `src/synthetic/*`, `src/retrieval/*`, `src/pipeline/end_to_end_draft.py`
- `data/synthetic/verified_v1.jsonl`, `holdout_val.jsonl`, `pilot_review_batch.json`
- `data/retrieval_index/bm25_bundle.pkl`, `bm25_metric.pkl`
- `stats/retrieval_eval.json`, `stats/week2_audit.json`

## Human
- Review `data/synthetic/pilot_review_batch.json` (câu có tự nhiên không)
- Quyết hướng Tuần 3 (self-repair text2pandas)
