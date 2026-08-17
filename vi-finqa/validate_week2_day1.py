import json
from pathlib import Path

import yaml


def validate() -> dict:
    tax_p = Path("src/synthetic/taxonomy.yaml")
    strat = Path("docs/synthetic_strategy.md")
    audit = Path("stats/week2_audit.json")
    tax = yaml.safe_load(tax_p.read_text(encoding="utf-8")) if tax_p.exists() else {}
    n_ok = 0
    for k, v in (tax or {}).items():
        if isinstance(v, dict) and v.get("desc") and v.get("example"):
            n_ok += 1
    text = strat.read_text(encoding="utf-8") if strat.exists() else ""
    has_table = "| category |" in text or "By category" in text
    result = {
        "taxonomy_keys": len(tax or {}),
        "taxonomy_complete": n_ok,
        "strategy_exists": strat.exists(),
        "strategy_has_real_dist": has_table and "placeholder" not in text.lower(),
        "audit_ok": False,
        "pass": False,
    }
    if audit.exists():
        a = json.loads(audit.read_text(encoding="utf-8"))
        result["audit_ok"] = bool(a.get("ok_to_proceed"))
    result["pass"] = (
        result["taxonomy_keys"] >= 10
        and result["taxonomy_complete"] >= 10
        and result["strategy_exists"]
        and result["strategy_has_real_dist"]
        and result["audit_ok"]
    )
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
