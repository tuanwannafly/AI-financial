# Working Notes outline (paper)

## 1. Motivation
Corpus-level Vietnamese FinQA over OCR statements; public HF has questions without answers.

## 2. Method
### 2.1 Data pipeline
HF `AIGuruTinix/ViFinQA` → HTML table extract (coverage 99.59%, 125k tables) → long format 332k rows.
### 2.2 Schema & ontology
Fuzzy normalize + review queue; canonical seed in `ontology.yaml`.
### 2.3 Synthetic
Template taxonomy 12 types; 6739 verified by pandas exec; gold never used to generate.
### 2.4 Retrieval
BM25 metric docs; R@20 81.3%; Hybrid/dense hook unused (no GPU/model this run).
### 2.5 Text-to-pandas + repair
Template generator + optional rule repair. Oracle exec 100%, first-try 51% then 86% E2E after intent templates. Repair delta 0.

## 3. Experiments
Gold n=160. Metrics: table F2, exec acc, answer acc. Ablation 5 configs.

## 4. Ablation
Frozen `no_ontology`. Repair/ensemble dropped.

## 5. Error analysis
Pre-fix: calc+multi_table logic errors. Post-fix: remaining retrieval_miss 19%.

## 6. Discussion / limitations
Template-only; F2 vs R@20 gap; CC BY-NC data; self-built gold.

## 7. Conclusion / future
LLM self-repair, dense index, official question alignment.
