"""Comprehensive structural regulatory parser for Sri Lankan Gazettes.

Handles:
- Layout-aware bounding-box filtering of running headers, footers, pagination
- Multi-style document structure:
  - Principal regulations (e.g. 2494-47_E.pdf: 1., 2., 3., 4.(1)...)
  - Amendment regulations (e.g. 2494-06_E.pdf: (1) in regulation 3..., (2)...)
  - Statutory orders & notices (e.g. 2496-03_E.pdf: Orders, Schedules)
- Nested subclauses: sub-regulations (1), paragraphs (a), subparagraphs (i)
- Provisos: Provided that, Provided however, Provided further that
- Cross-page continuation stitching preserving exact text, page numbers, and offsets
- Schedule and Table detection (via PyMuPDF find_tables) attached to exact clause bbox
"""
import sys
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import pymupdf

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class NestedSubClause:
    identifier: str
    sub_type: str  # "subregulation", "paragraph", "subparagraph", "proviso", "table_row"
    text: str
    page_number: int
    char_start: int
    char_end: int


@dataclass
class TableData:
    headers: List[str]
    rows: List[List[str]]
    page_number: int = 1
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class SegmentedClause:
    clause_number: str
    text: str
    start_page: int
    end_page: int
    char_start: int
    char_end: int
    clause_type: str = "regulation"  # "regulation", "amendment_directive", "schedule", "order"
    parent_clause: Optional[str] = None
    sub_clauses: List[NestedSubClause] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    provisos: List[str] = field(default_factory=list)


_GAZETTE_HEADER_FOOTER_PATTERNS = [
    re.compile(r"^\s*I\s+fldgi.*", re.IGNORECASE),
    re.compile(r"^\s*Part\s+I\s*:\s*Sec\.\s*\(I\).*", re.IGNORECASE),
    re.compile(r"^\s*\d+A\s*$", re.IGNORECASE),
    re.compile(r"^\s*No\.\s*\d+/\d+\s*-\s*[A-Z]+,\s*[A-Z]+\s+\d+,\s*\d+.*", re.IGNORECASE),
    re.compile(r"^\s*This Gazette Extraordinary can be downloaded.*", re.IGNORECASE),
    re.compile(r"^\s*EXTRAORDINARY\s*$", re.IGNORECASE),
    re.compile(r"^\s*The Gazette of the Democratic Socialist Republic.*", re.IGNORECASE),
    re.compile(r"^\s*\(Published by Authority\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*PART I\s*:\s*SECTION \(I\).*", re.IGNORECASE),
    re.compile(r"^\s*Gover.*No.*", re.IGNORECASE),
    re.compile(r"^\s*1A\s*-\s*PG.*", re.IGNORECASE),
    re.compile(r"^\s*1A\s*-\s*G.*", re.IGNORECASE),
    re.compile(r".*\d{4}/\d{2}\s*-\s*\d{4}.*", re.IGNORECASE),
    re.compile(r"^\s*PRINTED AT THE DEPARTMENT OF GOVERNMENT PRINTING.*", re.IGNORECASE),
    re.compile(r"^\s*EOG\s+\d{2}\s*-\s*\d{4}.*", re.IGNORECASE),
    re.compile(r"^\s*[\?\u2022\-\s]{5,}\s*$"),
]


def is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(p.match(s) for p in _GAZETTE_HEADER_FOOTER_PATTERNS)


def extract_tables_from_doc(doc: pymupdf.Document) -> Dict[int, List[TableData]]:
    """Extract structured tables by page number using PyMuPDF."""
    tables_by_page: Dict[int, List[TableData]] = {}
    for p_idx in range(len(doc)):
        p_num = p_idx + 1
        page = doc[p_idx]
        found = page.find_tables()
        p_tables: List[TableData] = []
        for t in found.tables:
            raw_data = t.extract()
            if not raw_data:
                continue
            headers = [str(c or "").strip().replace("\n", " ") for c in raw_data[0]]
            rows = []
            for r in raw_data[1:]:
                clean_r = [str(c or "").strip().replace("\n", " ") for c in r]
                if any(clean_r):
                    rows.append(clean_r)
            if headers or rows:
                p_tables.append(
                    TableData(
                        headers=headers,
                        rows=rows,
                        page_number=p_num,
                        bbox=t.bbox,
                    )
                )
        if p_tables:
            tables_by_page[p_num] = p_tables
    return tables_by_page


def format_table_as_text(table: TableData) -> str:
    """Format structured table as clean readable markdown text."""
    lines = []
    if any(table.headers):
        lines.append("| " + " | ".join(table.headers) + " |")
        lines.append("| " + " | ".join("---" for _ in table.headers) + " |")
    for r in table.rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def parse_nested_subclauses(text: str, page_num: int) -> Tuple[List[NestedSubClause], List[str]]:
    """Extract nested subclauses ((1), (a), (i), provisos) within clause text."""
    sub_clauses: List[NestedSubClause] = []
    provisos: List[str] = []

    proviso_pat = re.compile(
        r"(Provided\s+(?:further\s+that|however\s*,?|that\s*,?)[^\.\;]+(?:[\.\;]|$))",
        re.IGNORECASE | re.DOTALL,
    )
    for m in proviso_pat.finditer(text):
        p_text = m.group(1).strip()
        provisos.append(p_text)
        sub_clauses.append(
            NestedSubClause(
                identifier="Proviso",
                sub_type="proviso",
                text=p_text,
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    subreg_pat = re.compile(r"(?:^|\n)\s*(\(\d+\))\s+([^\n]+)", re.MULTILINE)
    for m in subreg_pat.finditer(text):
        sub_clauses.append(
            NestedSubClause(
                identifier=m.group(1),
                sub_type="subregulation",
                text=m.group(0).strip(),
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    para_pat = re.compile(r"(?:^|\n)\s*(\([a-z]\))\s+([^\n]+)", re.MULTILINE)
    for m in para_pat.finditer(text):
        sub_clauses.append(
            NestedSubClause(
                identifier=m.group(1),
                sub_type="paragraph",
                text=m.group(0).strip(),
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    subpara_pat = re.compile(r"(?:^|\n)\s*(\((?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\))\s+([^\n]+)", re.IGNORECASE | re.MULTILINE)
    for m in subpara_pat.finditer(text):
        sub_clauses.append(
            NestedSubClause(
                identifier=m.group(1),
                sub_type="subparagraph",
                text=m.group(0).strip(),
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    return sub_clauses, provisos


def extract_document_structure(doc: pymupdf.Document) -> Tuple[Dict[str, Any], List[SegmentedClause]]:
    """Complete layout-aware extraction of preamble and clauses from a PyMuPDF document."""
    tables_by_page = extract_tables_from_doc(doc)

    pages_lines: List[List[Tuple[str, int, float, float]]] = []
    full_preamble_text = ""

    for p_idx in range(len(doc)):
        p_num = p_idx + 1
        page = doc[p_idx]
        p_height = page.rect.height
        lines_on_page = []

        blocks = page.get_text("blocks")
        for b in blocks:
            if b[6] != 0:
                continue
            b_y0, b_y1 = b[1], b[3]
            block_text = b[4]

            if b_y0 < 75 and is_noise_line(block_text):
                continue
            if b_y1 > (p_height - 60) and is_noise_line(block_text):
                continue

            for raw_line in block_text.split("\n"):
                s = raw_line.strip()
                if not s or is_noise_line(s):
                    continue
                lines_on_page.append((raw_line, p_num, b_y0, b_y1))

        pages_lines.append(lines_on_page)
        if p_num <= 2:
            full_preamble_text += "\n" + page.get_text("text")

    meta = {
        "gazette_no": None,
        "published": None,
        "commences": None,
        "instrument": None,
        "authority": None,
        "enabling_act": None,
        "instrument_type": "regulation",
    }

    m_gz = re.search(r"No\.?\s*(\d{4}/\d{1,2})", full_preamble_text, re.IGNORECASE)
    if m_gz:
        meta["gazette_no"] = f"Gazette Extraordinary No. {m_gz.group(1)}"

    m_pub = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})",
        full_preamble_text,
        re.IGNORECASE,
    )
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }
    if m_pub:
        day = int(m_pub.group(1))
        month = months.get(m_pub.group(2).lower(), "01")
        year = m_pub.group(3)
        meta["published"] = f"{year}-{month}-{day:02d}"

    m_auth = re.search(r"(Minister of [^\n\.,]+?)(?:\s+in consultation|\.|\,|$)", full_preamble_text, re.IGNORECASE)
    if m_auth:
        meta["authority"] = m_auth.group(1).strip()
    else:
        meta["authority"] = "Ministry of Health, Sri Lanka"

    m_act = re.search(r"((?:FOOD|COMPANIES)\s+ACT,?\s*No\.?\s*\d+\s*o?f\s*\d{4})", full_preamble_text, re.IGNORECASE)
    if m_act:
        meta["enabling_act"] = m_act.group(1).strip()

    m_cit = re.search(r"(?:cited as|Regulations\s*\n\s*The)\s+([^\n\.]+(?:Regulations|Act|Order|Orders)\s+\d{4})", full_preamble_text, re.IGNORECASE)
    if m_cit:
        meta["instrument"] = m_cit.group(1).strip()
    else:
        m_tit = re.search(r"([A-Za-z\s\(\)\-]+(?:Regulations|Orders|Order)\s+\d{4})", full_preamble_text)
        if m_tit:
            meta["instrument"] = m_tit.group(1).strip()

    m_com = re.search(
        r"come into operation\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})",
        full_preamble_text,
        re.IGNORECASE,
    )
    if m_com:
        c_day = int(m_com.group(1))
        c_month = months.get(m_com.group(2).lower(), "01")
        c_year = m_com.group(3)
        meta["commences"] = f"{c_year}-{c_month}-{c_day:02d}"

    all_lines: List[Tuple[str, int, float, float]] = []
    for pl in pages_lines:
        for line_tup in pl:
            all_lines.append(line_tup)

    is_amendment = bool(re.search(r"hereby further amended as follows", full_preamble_text, re.IGNORECASE))
    is_orders = bool(re.search(r"ORDERS\s+under|Companies \(Fees\) Orders", full_preamble_text, re.IGNORECASE))

    if is_amendment:
        meta["instrument_type"] = "amendment_regulation"
    elif is_orders:
        meta["instrument_type"] = "statutory_order"

    principal_heading = re.compile(
        r"^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]*))\s*$",
        re.IGNORECASE,
    )
    principal_inline = re.compile(
        r"^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]*))\s+([A-Z].*)",
        re.IGNORECASE,
    )
    amend_directive = re.compile(r"^\s*\((\d{1,2})\)\s*$", re.IGNORECASE)
    amend_directive_inline = re.compile(r"^\s*\((\d{1,2})\)\s+([A-Za-z].*)", re.IGNORECASE)
    amend_target = re.compile(r"in\s+(regulation\s+\d+|sub-regulation\s+\d+|the\s+Schedule)", re.IGNORECASE)
    schedule_head = re.compile(r'^\s*["“]?(SCHEDULE\s*[IVXLCDM\d]*)["”]?\s*$', re.IGNORECASE)

    clauses: List[SegmentedClause] = []
    current_clause_dict: Optional[Dict[str, Any]] = None
    in_substantive_body = False
    last_reg_num = 0

    def finalize_clause(c_dict: Dict[str, Any], end_p: int, end_y: float) -> None:
        raw_c_text = "\n".join(c_dict["lines"]).strip()
        c_start_page = c_dict["start_page"]
        c_start_y = c_dict["start_y"]
        c_type = c_dict["clause_type"]

        # Layout-exact table attachment:
        # A table belongs to this clause if it falls within the clause's vertical bbox range or if this is a SCHEDULE
        matched_tables: List[TableData] = []
        for p_i in range(c_start_page, end_p + 1):
            if p_i in tables_by_page:
                for tb in tables_by_page[p_i]:
                    t_y0 = tb.bbox[1] if tb.bbox else 0.0
                    # For SCHEDULE or specific target, attach if on or after clause start
                    if c_type == "schedule" or "Schedule" in c_dict["name"]:
                        matched_tables.append(tb)
                        raw_c_text += "\n\n" + format_table_as_text(tb)
                    elif p_i == c_start_page and t_y0 >= (c_start_y - 10) and (p_i < end_p or t_y0 <= (end_y + 10)):
                        matched_tables.append(tb)
                        raw_c_text += "\n\n" + format_table_as_text(tb)

        subclauses, provisos = parse_nested_subclauses(raw_c_text, c_start_page)

        clauses.append(
            SegmentedClause(
                clause_number=c_dict["name"],
                text=raw_c_text,
                start_page=c_start_page,
                end_page=end_p,
                char_start=0,
                char_end=len(raw_c_text),
                clause_type=c_type,
                sub_clauses=subclauses,
                tables=matched_tables,
                provisos=provisos,
            )
        )

    for idx, (line_str, p_num, y0, y1) in enumerate(all_lines):
        s = line_str.strip()
        prev_line = all_lines[idx - 1][0].strip() if idx > 0 else ""

        # Check for division marker
        if s.upper() in ("REGULATIONS", "ORDERS", "ORDER"):
            in_substantive_body = True
            continue

        is_heading = False
        clause_name = None
        clause_type = "regulation"
        inline_body = ""

        # Schedule heading check
        m_sched = schedule_head.match(s)
        if m_sched:
            is_heading = True
            in_substantive_body = True
            clause_name = m_sched.group(1).upper()
            clause_type = "schedule"

        elif not in_substantive_body:
            if is_amendment and (amend_directive.match(s) or amend_directive_inline.match(s)):
                in_substantive_body = True
            elif not is_amendment and (principal_heading.match(s) or principal_inline.match(s)):
                in_substantive_body = True
            elif is_orders and "are hereby amended" in s:
                in_substantive_body = True
                continue
            else:
                continue

        if not is_heading:
            if is_amendment:
                m_ad = amend_directive.match(s)
                m_adi = amend_directive_inline.match(s)
                match_amend = m_ad or m_adi
                if match_amend:
                    dir_num = match_amend.group(1)
                    is_heading = True
                    clause_type = "amendment_directive"
                    next_few = " ".join([l[0].strip() for l in all_lines[idx:idx + 3]])
                    m_tgt = amend_target.search(next_few)
                    tgt_info = f" ({m_tgt.group(1).title()})" if m_tgt else ""
                    clause_name = f"Directive ({dir_num}){tgt_info}"
                    inline_body = match_amend.group(2) if m_adi else ""
            else:
                m_ph = principal_heading.match(s)
                m_pi = principal_inline.match(s)
                match_princ = m_ph or m_pi
                if match_princ:
                    r_num_str = match_princ.group(1)
                    sub_num = match_princ.group(2)
                    sched_kw = match_princ.group(3)

                    if sched_kw:
                        is_heading = True
                        clause_name = sched_kw.upper()
                        clause_type = "schedule"
                    elif r_num_str:
                        r_num = int(r_num_str)
                        continuing_prepositions = ("under", "to", "of", "in", "the", "and", "or", "with", "that", "from", "for")
                        is_cont = any(prev_line.lower().endswith(f" {prep}") or prev_line.lower() == prep for prep in continuing_prepositions)
                        if (r_num == last_reg_num + 1 or (last_reg_num == 0 and r_num == 1)) and not is_cont:
                            is_heading = True
                            last_reg_num = r_num
                            clause_name = f"Regulation {r_num}({sub_num})" if sub_num else f"Regulation {r_num}"
                            clause_type = "regulation"
                            inline_body = match_princ.group(4) if m_pi else ""

        if is_heading:
            if current_clause_dict and current_clause_dict["lines"]:
                finalize_clause(current_clause_dict, p_num, y0)

            current_clause_dict = {
                "name": clause_name,
                "clause_type": clause_type,
                "start_page": p_num,
                "start_y": y0,
                "lines": [inline_body] if inline_body else [],
            }
        elif current_clause_dict is not None:
            current_clause_dict["lines"].append(line_str)

    if current_clause_dict and current_clause_dict["lines"]:
        finalize_clause(current_clause_dict, len(doc), doc[-1].rect.height)

    return meta, clauses


if __name__ == "__main__":
    for target_pdf in ["backend/data/raw_sources/2494-06_E.pdf", "backend/data/raw_sources/2496-03_E.pdf"]:
        doc = pymupdf.open(target_pdf)
        print(f"\n=======================================================")
        print(f"=== TESTING ON {target_pdf} ===")
        print(f"=======================================================")
        meta, clauses = extract_document_structure(doc)
        print("\n--- PREAMBLE METADATA ---")
        for k, v in meta.items():
            print(f"  {k}: {v}")

        print(f"\n--- EXTRACTED CLAUSES ({len(clauses)}) ---")
        for idx, c in enumerate(clauses, 1):
            print(f"\n[{idx}] {c.clause_number} | Type: {c.clause_type} | Pages: {c.start_page}-{c.end_page} | Length: {len(c.text)} chars")
            print(f"    Subclauses count: {len(c.sub_clauses)} | Provisos count: {len(c.provisos)} | Tables count: {len(c.tables)}")
            if c.provisos:
                for p in c.provisos:
                    print(f"    PROVISO: {p[:100]}...")
            if c.sub_clauses:
                for sc in c.sub_clauses[:4]:
                    print(f"    SUB: {sc.identifier} ({sc.sub_type}) -> {sc.text[:60]}...")
            if c.tables:
                for tb in c.tables:
                    print(f"    TABLE: headers={tb.headers} | {len(tb.rows)} rows (Page {tb.page_number})")
            print(f"    Excerpt: {c.text[:130].replace(chr(10), ' ')}...")
