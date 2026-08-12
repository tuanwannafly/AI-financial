from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def append_jsonl(path: str | Path, event: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def write_status(day: int, content: str) -> Path:
    p = Path(f"status/day{day}_status.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def write_escalation(
    day: int,
    module: str,
    reason: str,
    tried: str,
    samples: str,
    need_decision: str,
) -> Path:
    ts = datetime.now(timezone.utc).isoformat()
    body = f"""## ESCALATION — {ts}
- Day: {day}
- Module: {module}
- Lý do dừng: {reason}
- Đã thử: {tried}
- File/case mẫu đính kèm: {samples}
- Cần người quyết: {need_decision}
"""
    p = Path(f"status/day{day}_escalation.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    append_jsonl(f"logs/day{day}_run.jsonl", {
        "event": "escalation",
        "module": module,
        "reason": reason,
    })
    return p
