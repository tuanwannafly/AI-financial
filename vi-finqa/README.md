# ViFinQA — Week 1 Data Foundation

Agent-executable Week 1 plan: each day has input/output contracts and `validate_dayN.py` gates.

## Bootstrap

```powershell
cd vi-finqa
py -m pip install -r requirements.txt
py validate_repo.py
```

## Day gates

| Day | Module | Validate |
|-----|--------|----------|
| 1 | Explore | `py validate_day1.py` |
| 2 | Heuristic extract | `py validate_day2.py` |
| 3 | Full corpus | `py validate_day3.py` |
| 4 | Ontology normalize | `py validate_day4.py` |
| 5 | Gold set | `py validate_day5.py` |
| 6 | Validator + scorer | `py validate_day6.py` |
| 7 | Report | `py validate_day7.py` |

## Key paths

- Raw: `data/raw/`
- Extracted: `data/extracted/metadata.jsonl`
- Ontology: `src/schema/ontology.yaml`
- Gold: `data/gold/gold_set.json`
- Status: `status/day{N}_status.md`
- Logs: `logs/day{N}_run.jsonl`
- Checkpoints: `checkpoints/day{N}.json`

## Escalation

Write `status/day{N}_escalation.md` using `docs/ESCALATION_TEMPLATE.md`. Do not invent answers past escalate rules.
