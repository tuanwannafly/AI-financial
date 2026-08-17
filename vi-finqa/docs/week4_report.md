# Week 4 Report — Final

## Priority / ROI
See `docs/week4_priority.md`. Chose generation_wrong_logic first (33% potential).

## Improvements with before/after
| | ok rate | answer_acc | gen_wrong |
|---|---|---|---|
| Day2 before | 46.25% | 53.1% | 33.1% |
| Day2 after (YoY/sum/ticker templates) | **72.5%** | **86.3%** | **8.1%** |
| Delta | **+26.3 pp** | +33.1 pp | −25 pp |

Dropped: LLM ensemble/repair (exec already saturated; ablation same as full).

## Ablation (`stats/ablation.json`)
| config | f2 | exec | answer_acc | ok |
|---|---|---|---|---|
| full | 0.318 | 0.944 | 0.863 | 0.725 |
| no_repair | 0.318 | 0.944 | 0.863 | 0.725 |
| no_ensemble | 0.318 | 0.944 | 0.863 | 0.725 |
| **no_ontology** | 0.315 | **1.00** | **0.919** | 0.725 |
| smaller_topk | **0.354** | 0.944 | 0.863 | 0.669 |

**Frozen:** `no_ontology` (0.5 F2 + 0.5 answer_acc). Combined score highest. Ontology expansion not required for template path.

## Ensemble / verifier
- Template dual-variant ensemble: no extra lift vs single template (same code).
- Rule verifier: unused in frozen (fail-open if LLM).
- **Not in frozen.**

## Post-process / notes_qa
- Unit helpers in `src/finalize/postprocess.py`
- notes/thuyet_minh gold: **30/30 numeric** — no text-QA escalate

## Submission
- `submissions/rehearsal.zip` → `submission_validator` **PASS 160/160**

## Repro
- `pip install -r requirements.txt`; `py -c "from src.pipeline.e2e import run_e2e"`
- Heavy data not in git — download HF + rebuild extract/index

## Rủi ro / limitation
- No LLM: ceiling is template coverage; official HF questions unmapped
- Table F2 low vs Recall@20 (metric docs share start_line; top-1 noisy)
- compare_companies retrieval still weak
- Last-minute: **no core logic change after freeze v1**

## Week 4+ / Future
Hyperparams, dense retriever, real LLM repair, paper polish, official test pack when labels exist.
