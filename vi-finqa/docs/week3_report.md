# Week 3 Report (completed in Week 4 catch-up)

Pipeline W3 modules were missing on disk (`e2e_eval.json` absent). Rebuilt template-first (no LLM key).

## Oracle vs Real (gold n=160)
- Oracle (gold CSV, no retrieval): exec_rate **100%**, first_try_answer_acc **51.25%** (serializer markdown=structured=json=relevant — templates ignore text)
- After intent templates (same oracle path conceptually): E2E answer_acc **86.25%** when using gold CSV + retrieve for tables
- Real E2E: retrieval_miss **19.4%**, generation_wrong_logic **8.1%** (after W4 Day2), exec fail **0%**

## Self-repair
- Delta exec_rate: **+0** (already 100% oracle). Rule-based repair kept as optional; **not frozen**.

## Serializers
- 4 implemented; oracle acc identical 51.25% under template generator → pick **markdown** for docs, no quality difference.

## Strategy comparison (later W4)
See `stats/ablation.json`. Repair=ensemble no lift.

## Nợ sang Tuần 4
- LLM generator/repair unused
- Retrieval F2 ~0.32 (R@20 81% but exact `id|line` top-k)
- Multi-table/compare still some misses
