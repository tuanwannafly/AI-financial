from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Tuple
import re
from html.parser import HTMLParser


@dataclass
class TableRecord:
    report_id: str
    start_line: int
    end_line: int
    table_type: str
    unit: str | None
    company: str | None
    year: int | None
    is_consolidated: bool | None
    raw_text: str
    rows: List[List[str]] = field(default_factory=list)
    source: str = "html"


# Statement title patterns (OCR-tolerant)
PAT_CDKT = re.compile(r"B[ẢA]NG\s+C[ÂAĂ]N\s+[ĐD][ỐOÔ]I\s+K[ẾEÊ]\s+TO[ÁA]N", re.I)
PAT_KQKD = re.compile(
    r"(B[ÁA]O\s+C[ÁA]O\s+)?K[ẾEÊ]T\s+QU[ẢA]\s+HO[ẠA]T\s+[ĐD][ỘO]NG\s+KINH\s+DOANH",
    re.I,
)
PAT_LCTT = re.compile(
    r"(B[ÁA]O\s+C[ÁA]O\s+)?L[ƯUÙÚỤỦỮ]\s*U?\s*CHUY[ÊEẾỀỂỄ]N\s+TI[ỀEÊẾỂỄ]N\s+T[ỆEÊẾỂỄ]",
    re.I,
)
PAT_THUYET = re.compile(r"THUY[ẾEÊ]T\s+MINH\s+(B[ÁA]O\s+C[ÁA]O|V[ỀEÊ]|S[ỐOÔ]|S[ỐOÔ]\s+\d)", re.I)
PAT_THUYET_TITLE = re.compile(r"^.{0,20}THUY[ẾEÊ]T\s+MINH\b", re.I)

TABLE_TYPE_PATTERNS = {
    "CDKT": PAT_CDKT,
    "KQKD": PAT_KQKD,
    "LCTT": PAT_LCTT,
}

UNIT_SIMPLE = re.compile(
    r"[ĐD][ơo]n\s+v[ịi]\s*[:：]?\s*(VND|VNĐ|đồng|Dong|triệu(?:\s+đồng)?|tỷ(?:\s+đồng)?|nghìn(?:\s+đồng)?)",
    re.IGNORECASE,
)
CONSOLIDATED_PATTERN = re.compile(r"H[ỢO]P\s+NH[ẤA]T|consolidated", re.IGNORECASE)
SEPARATE_PATTERN = re.compile(r"RI[ÊE]NG|separate", re.IGNORECASE)
NEGATIVE_NUM = re.compile(r"^\(([\d.,]+)\)$")
HTML_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
NUM_LIKE = re.compile(r"^\(?-?[\d.,]+\)?%?$")


class _TableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[str]] = []
        self._row: List[str] = []
        self._cell: List[str] = []
        self._in_td = False

    def handle_starttag(self, tag: str, attrs) -> None:
        t = tag.lower()
        if t == "tr":
            self._row = []
        elif t in ("td", "th"):
            self._in_td = True
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("td", "th") and self._in_td:
            text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append(text)
            self._in_td = False
            self._cell = []
        elif t == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = []

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._cell.append(data)


def parse_html_table(html: str) -> List[List[str]]:
    parser = _TableHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return []
    return parser.rows


def detect_statement_header(line: str) -> Optional[str]:
    """Detect statement title on a plain text line (not inside big HTML TOC)."""
    s = line.strip()
    if not s or len(s) > 200:
        # long HTML lines: only accept if short title-like after stripping tags
        plain = re.sub(r"<[^>]+>", " ", s)
        plain = re.sub(r"\s+", " ", plain).strip()
        if len(plain) > 120:
            return None
        s = plain

    # skip pure TOC rows listing many titles
    if s.upper().count("TRANG") and s.count("<td") > 3:
        return None

    if PAT_CDKT.search(s):
        return "CDKT"
    if PAT_KQKD.search(s):
        return "KQKD"
    if PAT_LCTT.search(s):
        return "LCTT"
    if PAT_THUYET.search(s) or (PAT_THUYET_TITLE.search(s) and "Mã số" not in s and "Ma so" not in s):
        # only title-like thuyết minh, not column header "Thuyết minh"
        if re.search(r"Thuyết minh\s*</td>", line, re.I):
            return None
        return "THUYET_MINH"
    return None


def infer_type_from_rows(rows: List[List[str]]) -> str:
    if not rows:
        return "UNKNOWN"
    header = " ".join(rows[0]).lower()
    blob = " ".join(" ".join(r) for r in rows[:12])
    blob_l = blob.lower()

    # TOC
    if "trang" in header and len(rows) <= 25 and not _has_money_cells(rows):
        return "TOC"

    # CDKT structure
    if any(k in blob_l for k in ("tài sản ngắn hạn", "tai san ngan han", "a. tài sản", "nguồn vốn", "nguon von", "nợ phải trả", "no phai tra")):
        if any(k in blob_l for k in ("mã số", "ma so", "31/12", "01/01")):
            return "CDKT"
    if re.search(r"T[ÀA]I\s+S[ẢA]N", blob, re.I) and re.search(r"M[ãa]\s+s[ốo]", blob, re.I):
        return "CDKT"

    # KQKD
    if any(
        k in blob_l
        for k in (
            "doanh thu bán hàng",
            "doanh thu ban hang",
            "giá vốn hàng bán",
            "gia von hang ban",
            "lợi nhuận sau thuế",
            "loi nhuan sau thue",
            "chi phí quản lý",
        )
    ):
        return "KQKD"

    # LCTT
    if any(
        k in blob_l
        for k in (
            "lưu chuyển tiền",
            "luu chuyen tien",
            "lợi nhuận kế toán trước thuế",
            "loi nhuan ke toan truoc thue",
            "hoạt động kinh doanh",
        )
    ) and ("mã số" in blob_l or "ma so" in blob_l or "năm" in blob_l):
        # distinguish from KQKD: LCTT often has "khấu hao" / "tăng giảm"
        if any(k in blob_l for k in ("khấu hao", "khau hao", "tăng, giảm", "chi khác", "thu khác từ", "lưu chuyển tiền thuần")):
            return "LCTT"
        if "i. lưu" in blob_l or "lưu chuyên" in blob_l or "luu chuyen" in blob_l:
            return "LCTT"

    if re.search(r"L[ƯU]U\s+CHUY", blob, re.I):
        return "LCTT"

    return "UNKNOWN"


def _has_money_cells(rows: List[List[str]]) -> bool:
    n = 0
    for row in rows:
        for cell in row:
            c = cell.strip()
            if not c:
                continue
            if normalize_number(c) is not None:
                n += 1
            elif re.search(r"\d{1,3}(?:\.\d{3}){2,}", c):  # 1.234.567 style
                n += 1
            if n >= 3:
                return True
    return False


def normalize_number(tok: str) -> float | None:
    tok = tok.strip().replace(" ", "")
    neg = NEGATIVE_NUM.match(tok)
    if neg:
        tok = neg.group(1)
        sign = -1
    else:
        sign = 1
    if not re.fullmatch(r"[\d.,]+", tok):
        return None
    # VN accounting: '.' thousands, ',' decimal (or pure thousand groups)
    if "," in tok and "." in tok:
        tok = tok.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok):
        tok = tok.replace(".", "")
    elif tok.count(".") > 1:
        tok = tok.replace(".", "")
    elif "," in tok and "." not in tok:
        # '1,234' thousands OR '1,5' decimal — 3 digits after comma => thousands
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", tok):
            tok = tok.replace(",", "")
        else:
            tok = tok.replace(",", ".")
    try:
        return sign * float(tok)
    except ValueError:
        return None


def _meta_from_path(file_path: Path) -> Tuple[Optional[str], Optional[int], Optional[bool]]:
    parts = file_path.parts
    company = None
    year = None
    try:
        idx = parts.index("financial_statements")
        if idx + 1 < len(parts):
            company = parts[idx + 1]
        if idx + 2 < len(parts):
            y = parts[idx + 2]
            if y.isdigit():
                year = int(y)
    except ValueError:
        pass

    stem = file_path.stem.lower()
    is_cons: Optional[bool] = None
    if CONSOLIDATED_PATTERN.search(stem) or "consolidated" in stem:
        is_cons = True
    elif SEPARATE_PATTERN.search(stem) or "separate" in stem:
        is_cons = False
    return company, year, is_cons


def _is_financial_table(rows: List[List[str]]) -> bool:
    if not rows or len(rows) < 2:
        return False
    if _has_money_cells(rows):
        return True
    header = " ".join(rows[0]).lower()
    if any(k in header for k in ("mã số", "ma so", "chỉ tiêu", "chi tieu", "tài sản", "nguồn vốn")):
        return len(rows) >= 3
    return False


def _is_toc_table(rows: List[List[str]]) -> bool:
    if not rows:
        return False
    header = " ".join(rows[0]).upper()
    if "TRANG" in header:
        return True
    # many short page-number cells
    page_cells = 0
    for row in rows[1:6]:
        if row and re.fullmatch(r"\d{1,3}(\s*[-–]\s*\d{1,3})?", row[-1].strip() or ""):
            page_cells += 1
    return page_cells >= 3 and not _has_money_cells(rows)


def extract_tables(file_path: Path, report_id: str) -> List[TableRecord]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    company, year, is_consolidated = _meta_from_path(file_path)
    if is_consolidated is None:
        is_consolidated = bool(CONSOLIDATED_PATTERN.search(file_path.stem))

    records: List[TableRecord] = []

    # line -> unit / statement header
    line_units: dict[int, str] = {}
    line_headers: dict[int, str] = {}
    for i, line in enumerate(lines):
        um = UNIT_SIMPLE.search(line)
        if um:
            line_units[i] = um.group(0).strip()
        # only plain-ish lines for headers
        if "<table" in line.lower() and line.lower().count("<td") > 4:
            continue
        ttype = detect_statement_header(line)
        if ttype:
            line_headers[i] = ttype

    for m in HTML_TABLE_RE.finditer(text):
        html = m.group(0)
        start_char = m.start()
        start_line = text.count("\n", 0, start_char)
        end_line = start_line + html.count("\n")
        rows = parse_html_table(html)
        if not rows:
            continue
        if _is_toc_table(rows):
            continue

        unit = None
        for li in range(max(0, start_line - 10), start_line + 1):
            if li in line_units:
                unit = line_units[li]

        # nearest preceding statement header
        ttype: Optional[str] = None
        header_line = start_line
        for li in range(start_line, max(-1, start_line - 20), -1):
            if li in line_headers and line_headers[li] in ("CDKT", "KQKD", "LCTT", "THUYET_MINH"):
                # main statements: only stick if close; notes can stick a bit further
                dist = start_line - li
                ht = line_headers[li]
                if ht in ("CDKT", "KQKD", "LCTT") and dist <= 15:
                    ttype = ht
                    header_line = li
                    break
                if ht == "THUYET_MINH" and dist <= 20:
                    ttype = ht
                    header_line = li
                    break

        content_type = infer_type_from_rows(rows)

        # Prefer content type for main statements when header is missing/wrong
        if content_type in ("CDKT", "KQKD", "LCTT"):
            if ttype is None or ttype == "THUYET_MINH" or ttype == "UNKNOWN":
                ttype = content_type
            elif ttype == "CDKT" and content_type in ("KQKD", "LCTT"):
                ttype = content_type
            elif ttype in ("KQKD", "LCTT") and content_type == "CDKT" and (start_line - header_line) > 5:
                ttype = content_type
        elif ttype is None:
            ttype = content_type

        if ttype in (None, "TOC", "UNKNOWN"):
            if not _is_financial_table(rows):
                continue
            ttype = "UNKNOWN"

        if ttype == "THUYET_MINH" and not _is_financial_table(rows):
            continue

        records.append(
            TableRecord(
                report_id=report_id,
                start_line=header_line,
                end_line=end_line,
                table_type=ttype,
                unit=unit,
                company=company,
                year=year,
                is_consolidated=is_consolidated,
                raw_text=html if len(html) < 50000 else html[:50000],
                rows=rows,
                source="html",
            )
        )

    # Plain-text fallback (smoke / non-HTML)
    if not any(r.source == "html" for r in records):
        current_unit = None
        i = 0
        while i < len(lines):
            line = lines[i]
            um = UNIT_SIMPLE.search(line)
            if um:
                current_unit = um.group(0).strip()
            ttype = detect_statement_header(line)
            if ttype and ttype in ("CDKT", "KQKD", "LCTT"):
                start = i
                body: List[str] = []
                j = i + 1
                blank_streak = 0
                while j < len(lines):
                    nt = detect_statement_header(lines[j])
                    if nt and nt in ("CDKT", "KQKD", "LCTT") and nt != ttype:
                        break
                    if lines[j].strip() == "":
                        blank_streak += 1
                        if blank_streak >= 3:
                            break
                    else:
                        blank_streak = 0
                        body.append(lines[j])
                    j += 1
                rows = [
                    re.split(r"\s{2,}|\t", r.strip())
                    for r in body
                    if r.strip() and not r.strip().startswith("=====")
                ]
                records.append(
                    TableRecord(
                        report_id=report_id,
                        start_line=start,
                        end_line=j - 1,
                        table_type=ttype,
                        unit=current_unit,
                        company=company,
                        year=year,
                        is_consolidated=is_consolidated,
                        raw_text="\n".join(body),
                        rows=rows,
                        source="plain",
                    )
                )
                i = j
            else:
                i += 1

    return records


def table_record_to_dict(record: TableRecord) -> dict:
    return asdict(record)


# backward-compat alias used in plan snippets
def detect_table_type(line: str) -> Optional[str]:
    return detect_statement_header(line)
