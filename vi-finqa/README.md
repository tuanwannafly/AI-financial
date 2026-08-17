# ViFinQA — End-to-end Vietnamese financial QA (v2)

Pipeline: OCR BCTC → tables → long format → synthetic QA → BM25 retrieval → template/LLM pandas → sandbox verify → submission zip.

`frozen/v1` remains unchanged as a rollback baseline. The v2 official pack
uses the complete metric catalog, company-name aliases, statement scope,
unit conversion, grounded evidence rows and deterministic query plans.

## Setup (Windows)

```powershell
cd vi-finqa
py -m pip install -r requirements.txt
$env:PYTHONIOENCODING = "utf-8"
py validate_repo.py
```

Download corpus (not in git):

```powershell
py -m src.utils.download_cli --repo_id AIGuruTinix/ViFinQA --local_dir data/raw
```

Rebuild heavy artifacts locally:

```powershell
py -m src.extraction.run_full data/raw --jobs 6 --batch-size 50
py -m src.schema.run_normalize
py -m src.schema.attach_canonical
py -m src.gold.build_gold_set --min_n 150
py -m src.retrieval.build_index_metric
```

## Run E2E + official pack

```powershell
py -m src.pipeline.e2e
py -m src.finalize.ablation
py -m src.finalize.pack_official --out submissions/submission.zip
# Optional local open-weight planner (Qwen2.5-7B-Instruct by default)
py -m src.finalize.pack_official --llm --out submissions/submission_llm.zip
```

The official packer reads all questions in `data/raw/questions/questions.jsonl`
by default. Use `--n 506` only when the dashboard explicitly requests a
506-question public subset. It writes `stats/official_pack_audit.json` and
uses `submissions/_pack_v2/` as a non-destructive staging directory.

## Validation

```powershell
py validators/submission_validator.py submissions/submission.zip --expected-n 1012
```

The validator checks the official JSON schema, complete IDs, safe CSV paths,
unique evidence variables/tables, and pandas query syntax. The packer also
executes every query before writing the ZIP.

## Week gates

| Week | Validate |
|------|----------|
| 1 | `validate_day1.py` … `validate_day7.py` |
| 2 | `validate_week2.py` |
| 3–4 | `stats/e2e_eval.json`, `stats/ablation.json`, `stats/official_pack_audit.json` |

## Layout

```
src/extraction    tables from HTML OCR
src/schema        ontology + longify
src/gold          execution-verified gold
src/synthetic     template synthetic (≥5k)
src/retrieval     BM25 (+ Hybrid hook)
src/text2pandas   serialize + template/LLM generator + repair
src/pipeline      e2e.py
src/finalize      query plan, official pack, ROI, ablation, freeze
validators/       submission_validator + local_scorer
data/gold/        gold_set.json (in git); evidence/ local
frozen/v1/        snapshot src + gold JSON
```

## Headline numbers (local eval on 160 gold)

| | |
|---|---|
| Extract coverage | 99.59% |
| Synthetic verified | 6,739 |
| Recall@20 | 81.3% |
| Oracle exec / first-try acc (pre-YoY templates) | 100% / 51.3% |
| E2E after Day-2 templates | ok 72.5%, answer_acc **86.3%**, F2 0.32 |
| Rehearsal validator | PASS 160/160 |

Gold is eval-only. Answers never trusted without sandbox/inline execution.

Dataset: [AIGuruTinix/ViFinQA](https://huggingface.co/datasets/AIGuruTinix/ViFinQA) (CC BY-NC OCR source).
