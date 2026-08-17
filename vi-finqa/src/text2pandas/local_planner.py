"""Optional local-only planner for ambiguous official questions.

The model is never asked to invent values or source documents.  It can only
choose one of the deterministic operation names after seeing grounded metric
labels.  The packer remains fully usable when transformers/model weights are
not installed.
"""
from __future__ import annotations

import json
import os
import re


ALLOWED_OPERATIONS = {
    "lookup",
    "sum",
    "difference",
    "ratio",
    "pct_change",
    "year_delta",
    "argmax",
    "argmin",
    "argmax_ratio",
    "argmin_ratio",
    "mean",
    "count",
}


class LocalQueryPlanner:
    def __init__(self, model_name: str | None = None, max_new_tokens: int = 128):
        self.model_name = model_name or os.getenv("VIFINQA_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        self.max_new_tokens = max_new_tokens
        self._pipeline = None

    def _load(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("transformers chưa được cài; dùng deterministic planner") from exc
        self._pipeline = pipeline(
            "text-generation",
            model=self.model_name,
            tokenizer=self.model_name,
            trust_remote_code=False,
        )
        return self._pipeline

    def plan(self, question: str, metric_labels: list[str]) -> dict | None:
        labels = list(dict.fromkeys(str(label) for label in metric_labels if label))
        prompt = (
            "You are a Vietnamese financial query planner. Return JSON only.\n"
            "Allowed operation values: lookup, sum, difference, ratio, pct_change, "
            "year_delta, argmax, argmin, argmax_ratio, argmin_ratio, mean, count.\n"
            "Do not calculate values. Do not invent metrics. Choose only from the "
            "provided metric labels.\n"
            f"Metric labels: {json.dumps(labels, ensure_ascii=False)}\n"
            f"Question: {question}\n"
            'JSON schema: {"operation":"lookup","metric_labels":[]}\n'
        )
        output = self._load()(prompt, max_new_tokens=self.max_new_tokens, do_sample=False)
        if not output:
            return None
        generated = output[0].get("generated_text", "")
        matches = re.findall(r"\{[^{}]*\}", generated, re.DOTALL)
        result = None
        for candidate in reversed(matches):
            try:
                result = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if not isinstance(result, dict):
            return None
        operation = result.get("operation")
        if operation not in ALLOWED_OPERATIONS:
            return None
        selected = [label for label in result.get("metric_labels", []) if label in labels]
        return {"operation": operation, "metric_labels": selected}
