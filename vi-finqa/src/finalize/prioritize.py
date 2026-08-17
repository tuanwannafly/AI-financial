from __future__ import annotations


def estimate_roi(e2e_breakdown: dict, total_gold: int) -> list[dict]:
    priorities = []
    bd = e2e_breakdown.get("breakdown") or e2e_breakdown
    for category, count in bd.items():
        if category == "ok":
            continue
        priorities.append(
            {
                "category": category,
                "count": count,
                "potential_score_gain_pct": count / total_gold * 100 if total_gold else 0,
            }
        )
    return sorted(priorities, key=lambda x: -x["potential_score_gain_pct"])


def select_improvement_targets(priority_list: list[dict], max_targets: int = 3, min_impact_pct: float = 5.0) -> list[str]:
    eligible = [p for p in priority_list if p["potential_score_gain_pct"] >= min_impact_pct]
    return [p["category"] for p in eligible[:max_targets]]


IMPROVEMENT_MAP = {
    "generation_wrong_logic": "intent_specific_prompt + dynamic_fewshot + multi_table_2stage",
    "execution_fail_unrepaired": "harden_repair_with_column_hints",
    "retrieval_miss": "refine_query_expansion_representation",
    "unit_mismatch": "unit_postprocessing",
}
