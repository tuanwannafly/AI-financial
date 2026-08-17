from __future__ import annotations

import json
import shutil
from pathlib import Path


def freeze_pipeline(version_tag: str, config_name: str) -> str:
    dest = Path(f"frozen/{version_tag}")
    dest.mkdir(parents=True, exist_ok=True)
    for d in ["src", "validators", "data/gold/gold_set.json", "data/gold/human_review_batch.json"]:
        src = Path(d)
        if not src.exists():
            continue
        target = dest / src.name
        if src.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "data").mkdir(exist_ok=True)
            (dest / "data" / "gold").mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / "data" / "gold" / src.name)
    (dest / "manifest.json").write_text(
        json.dumps({"version": version_tag, "ablation_config_used": config_name}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(dest)
