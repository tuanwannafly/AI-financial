import random
import re
from pathlib import Path
from typing import List, Dict, Any


def sample_files(raw_dir: str, n: int = 25, seed: int = 42) -> List[Path]:
    files = list(Path(raw_dir).rglob("*.txt"))
    random.Random(seed).shuffle(files)
    return files[:n]


TABLE_HEADER_HINTS = [
    r"BẢNG CÂN ĐỐI KẾ TOÁN",
    r"KẾT QUẢ HOẠT ĐỘNG KINH DOANH",
    r"LƯU CHUYỂN TIỀN TỆ",
    r"THUYẾT MINH",
    r"Đơn vị.{0,10}(triệu|tỷ|nghìn)",
]


def scan_file(path: Path) -> Dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    hits = {h: [] for h in TABLE_HEADER_HINTS}
    for i, line in enumerate(lines):
        for h in TABLE_HEADER_HINTS:
            if re.search(h, line, re.IGNORECASE):
                hits[h].append(i)
    return {"path": str(path), "n_lines": len(lines), "hits": hits}
