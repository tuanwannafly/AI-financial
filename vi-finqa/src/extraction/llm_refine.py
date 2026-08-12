from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


LLM_VERIFY_SYSTEM = (
    "Bạn là trợ lý kiểm tra trích xuất bảng tài chính từ báo cáo tài chính Việt Nam.\n"
    "Chỉ trả về JSON, không thêm chữ nào khác."
)

LLM_VERIFY_USER = """Đoạn văn bản sau được trích từ dòng {start_line} đến {end_line} của file {report_id}.
Xác định:
1. Đây có phải một bảng số liệu tài chính hợp lệ không?
2. table_type đúng là gì: CDKT | KQKD | LCTT | THUYET_MINH | UNKNOWN
3. start_line thực tế của bảng (có thể lệch so với đề xuất ban đầu)
4. Đơn vị tính (unit) nếu tìm thấy trong đoạn hoặc ngữ cảnh lân cận

Đoạn văn bản:
\"\"\"
{raw_text}
\"\"\"

Trả về đúng format:
{{\"is_valid_table\": bool, \"table_type\": str, \"corrected_start_line\": int, \"unit\": str|null}}
"""


def build_verify_prompt(report_id: str, start_line: int, end_line: int, raw_text: str) -> Dict[str, str]:
    return {
        "system": LLM_VERIFY_SYSTEM,
        "user": LLM_VERIFY_USER.format(
            report_id=report_id,
            start_line=start_line,
            end_line=end_line,
            raw_text=raw_text[:4000],
        ),
    }


def parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def needs_llm_assist(record: dict) -> bool:
    rows = record.get("rows") or []
    ttype = record.get("table_type")
    return len(rows) < 3 or ttype in (None, "UNKNOWN")
