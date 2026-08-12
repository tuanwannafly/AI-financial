"""Smoke test table extractor on synthetic BCTC-like text."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.extraction.table_extractor import extract_tables, normalize_number

SAMPLE = """BÁO CÁO TÀI CHÍNH HỢP NHẤT
Công ty Cổ phần Mẫu VNM

Đơn vị: triệu đồng

BẢNG CÂN ĐỐI KẾ TOÁN
Tài sản ngắn hạn          1.234.567          1.100.000
Tiền và tương đương tiền    100.000             90.000
Hàng tồn kho                50.000             45.000


KẾT QUẢ HOẠT ĐỘNG KINH DOANH
Doanh thu thuần           603.689            580.000
Lợi nhuận sau thuế         12.345             10.000
Lãi cơ bản trên cổ phiếu        5,2               4,8


BÁO CÁO LƯU CHUYỂN TIỀN TỆ
Lưu chuyển tiền thuần từ HĐKD   8.000           7.500


THUYẾT MINH
1. Tiền và tương đương tiền
Chi tiết: 100.000 (90.000)
"""


def main() -> int:
    raw = ROOT / "data" / "raw" / "_smoke"
    raw.mkdir(parents=True, exist_ok=True)
    f = raw / "VNM_2023_BCTC_HOP_NHAT.txt"
    f.write_text(SAMPLE, encoding="utf-8")

    recs = extract_tables(f, report_id=f.stem)
    assert normalize_number("1.234.567") == 1234567.0
    assert normalize_number("(1.234)") == -1234.0
    assert len(recs) >= 3, f"expected >=3 tables, got {len(recs)}: {[r.table_type for r in recs]}"
    types = {r.table_type for r in recs}
    assert "CDKT" in types and "KQKD" in types

    out = {
        "n_tables": len(recs),
        "types": [r.table_type for r in recs],
        "is_consolidated": recs[0].is_consolidated if recs else None,
        "pass": True,
    }
    stats = ROOT / "stats" / "smoke_extractor.json"
    stats.parent.mkdir(parents=True, exist_ok=True)
    stats.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
