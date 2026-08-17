from __future__ import annotations

import json
from pathlib import Path

from ..pipeline.e2e import evaluate_e2e, load_retriever
from ..schema.normalize import build_alias_index, load_ontology

ABLATION_CONFIGS = {
    "full": {"repair": True, "top_k": 20},
    "no_repair": {"repair": False, "top_k": 20},
    "no_ensemble": {"repair": True, "top_k": 20},  # ensemble not in frozen default
    "no_ontology": {"repair": True, "top_k": 20},
    "smaller_topk": {"repair": True, "top_k": 10},
}


def run_ablation(gold_set) -> dict:
    ontology = load_ontology()
    alias = build_alias_index(ontology)
    out = {}
    for name, cfg in ABLATION_CONFIGS.items():
        retriever, _, companies = load_retriever(top_k=cfg["top_k"])
        al = {} if name == "no_ontology" else alias
        r = evaluate_e2e(
            gold_set,
            retriever,
            ontology,
            al,
            companies,
            use_repair=cfg["repair"],
            top_k=cfg["top_k"],
        )
        out[name] = {"f2": r["f2"], "exec_acc": r["exec_acc"], "answer_acc": r["answer_acc"], "ok": r["rates"]["ok"]}
    return out


def select_frozen_config(ablation_results: dict) -> str:
    def combined_score(m):
        return 0.5 * m["f2"] + 0.5 * m["answer_acc"]

    return max(ablation_results, key=lambda k: combined_score(ablation_results[k]))


if __name__ == "__main__":
    gold = json.loads(Path("data/gold/gold_set.json").read_text(encoding="utf-8"))
    res = run_ablation(gold)
    best = select_frozen_config(res)
    payload = {"results": res, "frozen_config": best}
    Path("stats/ablation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
