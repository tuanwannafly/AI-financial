from __future__ import annotations

import json
from pathlib import Path

import yaml

from .analyze_gold import analyze_gold_distribution, analyze_long_coverage
from .audit_week1 import audit_week1


def write_strategy(
    out_path: str = "docs/synthetic_strategy.md",
    taxonomy_path: str = "src/synthetic/taxonomy.yaml",
) -> dict:
    audit = audit_week1()
    gold = analyze_gold_distribution()
    longc = analyze_long_coverage()
    tax = yaml.safe_load(Path(taxonomy_path).read_text(encoding="utf-8"))

    lines = [
        "# Synthetic Data Strategy (Week 2 Day 1)",
        "",
        "## Audit Week 1",
        "",
        f"- coverage: **{audit['coverage']:.4f}**",
        f"- gold_n: **{audit['gold_n']}**",
        f"- verified_ratio: **{audit['verified_ratio']:.4f}**",
        f"- action: `{audit['action']}`",
        "",
        "## Gold distribution (thật)",
        "",
        f"- n_total: {gold['n_total']}",
        f"- verified: {gold['verified']}",
        f"- n_companies (from meta): {gold['n_companies']}",
        "",
        "### By category",
        "",
        "| category | n |",
        "|---|---|",
    ]
    for k, v in sorted(gold["by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "### By year (meta)",
        "",
        "| year | n |",
        "|---|---|",
    ]
    for k, v in gold["by_year"].items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "### Top companies in gold meta",
        "",
        "| company | n |",
        "|---|---|",
    ]
    for c, n in gold["top_companies"]:
        lines.append(f"| {c} | {n} |")

    lines += [
        "",
        "## Long-format coverage (source for templates)",
        "",
        f"- n_rows: {longc.get('n_rows')}",
        f"- n_mapped: {longc.get('n_mapped')}",
        f"- n_companies: {longc.get('n_companies')}",
        "",
        "### Top canonical metrics",
        "",
        "| canonical | n |",
        "|---|---|",
    ]
    for c, n in longc.get("top_canonical") or []:
        lines.append(f"| {c} | {n} |")

    lines += [
        "",
        "## Gaps vs Week 2 taxonomy",
        "",
        "Gold Week 1 dùng 5 category nội bộ (`simple_lookup`…). Taxonomy Week 2 có 12 loại.",
        "Các loại **chưa** có trong gold hoặc mỏng: `ratio_structure`, `financial_index`,",
        "`multi_year_trend`, `unit_rounding`, `negative_edge_case`.",
        "Generator template sẽ ưu tiên các loại này trên long-mapped index.",
        "",
        "## Generation policy",
        "",
        "1. Template-first (không LLM) — mỗi sample verify bằng pandas trên CSV thật.",
        "2. Rule-based paraphrase (giữ query + answer).",
        "3. LLM optional nếu có API key (không block AC).",
        "4. Gold set **không** dùng để train/generate thêm — chỉ few-shot wording + eval.",
        "5. Dedup câu hỏi (token Jaccard / embedding nếu có).",
        "",
        "## Taxonomy keys",
        "",
        "| key | desc |",
        "|---|---|",
    ]
    for k, meta in tax.items():
        lines.append(f"| `{k}` | {meta.get('desc','')} |")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"audit": audit, "taxonomy_n": len(tax), "strategy": out_path}


if __name__ == "__main__":
    print(json.dumps(write_strategy(), ensure_ascii=False, indent=2))
