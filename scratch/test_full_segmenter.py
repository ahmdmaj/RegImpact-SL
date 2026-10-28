import fitz
import re
import sys
from typing import List, Dict, Any
from dataclasses import dataclass

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

@dataclass
class SegmentedClause:
    clause_number: str
    text: str
    start_page: int
    end_page: int
    char_start: int
    char_end: int

_GAZETTE_HEADER_FOOTER_PATTERNS = [
    re.compile(r'^\s*I\s+fldgi.*', re.IGNORECASE),
    re.compile(r'^\s*Part\s+I\s*:\s*Sec\.\s*\(I\).*', re.IGNORECASE),
    re.compile(r'^\s*\d+A\s*$', re.IGNORECASE),
    re.compile(r'^\s*No\.\s*\d+/\d+\s*-\s*[A-Z]+,\s*[A-Z]+\s+\d+,\s*\d+.*', re.IGNORECASE),
    re.compile(r'^\s*This Gazette Extraordinary can be downloaded.*', re.IGNORECASE),
    re.compile(r'^\s*EXTRAORDINARY\s*$', re.IGNORECASE),
    re.compile(r'^\s*The Gazette of the Democratic Socialist Republic.*', re.IGNORECASE),
    re.compile(r'^\s*\(Published by Authority\)\s*$', re.IGNORECASE),
    re.compile(r'^\s*PART I\s*:\s*SECTION \(I\).*', re.IGNORECASE),
    re.compile(r'^\s*Gover.*No.*', re.IGNORECASE),
    re.compile(r'^\s*1A\s*-\s*PG.*', re.IGNORECASE),
    re.compile(r'.*\d{4}/\d{2}\s*-\s*\d{4}.*', re.IGNORECASE),
    re.compile(r'^\s*[\?\u2022\-\s]{5,}\s*$'),
]

def is_gazette_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(p.match(s) for p in _GAZETTE_HEADER_FOOTER_PATTERNS)

def extract_document_preamble(pages: List[Any]) -> Dict[str, Any]:
    full_text = ""
    for p in pages[:4]:
        raw = getattr(p, "raw_text", None) or getattr(p, "text", None) or str(p)
        full_text += "\n" + raw

    meta = {
        "gazette_no": None,
        "published": None,
        "commences": None,
        "instrument": None,
        "authority": None,
        "enabling_act": None,
    }

    # Gazette No (e.g., 2494/47 or 1688/28)
    m_gz = re.search(r"No\.?\s*(\d{4}/\d{1,2})", full_text, re.IGNORECASE)
    if m_gz:
        meta["gazette_no"] = f"Gazette Extraordinary No. {m_gz.group(1)}"

    # Published date (e.g. 26th June, 2026 or 2026.06.26)
    m_pub = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})", full_text, re.IGNORECASE)
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

    # Authority (e.g. Minister of Health...)
    m_auth = re.search(r"(Minister of [^\n\.,]+)", full_text, re.IGNORECASE)
    if m_auth:
        meta["authority"] = m_auth.group(1).strip()
    else:
        meta["authority"] = "Ministry of Health, Sri Lanka"

    # Enabling act (e.g. Food Act, No. 26 of 1980)
    m_act = re.search(r"(Food Act,\s*No\.\s*\d+\s*of\s*\d{4})", full_text, re.IGNORECASE)
    if m_act:
        meta["enabling_act"] = m_act.group(1).strip()

    # Citation & commencement in Regulation 1
    m_cit = re.search(r"cited as\s+([^\n\.]+(?:Regulations|Act|Order)\s+\d{4})", full_text, re.IGNORECASE)
    if m_cit:
        meta["instrument"] = m_cit.group(1).strip()

    m_com = re.search(r"come into operation\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})", full_text, re.IGNORECASE)
    if m_com:
        c_day = int(m_com.group(1))
        c_month = months.get(m_com.group(2).lower(), "01")
        c_year = m_com.group(3)
        meta["commences"] = f"{c_year}-{c_month}-{c_day:02d}"

    return meta

def segment_document_clauses(pages: List[Any], min_clause_length: int = 40) -> List[SegmentedClause]:
    reg_heading_pattern = re.compile(
        r'^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]+))\s*$',
        re.IGNORECASE
    )
    reg_inline_pattern = re.compile(
        r'^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]+))\s+([A-Z].*)',
        re.IGNORECASE
    )

    doc_lines = []
    in_regulations = False
    for p_idx, p in enumerate(pages):
        p_num = getattr(p, "page_number", p_idx + 1)
        raw = getattr(p, "raw_text", None) or getattr(p, "text", None) or str(p)
        for line in raw.split("\n"):
            if is_gazette_noise(line):
                continue
            s = line.strip()
            if s.upper() == "REGULATIONS":
                in_regulations = True
                continue
            if in_regulations:
                doc_lines.append((p_num, line))

    clauses: List[SegmentedClause] = []
    current_clause = None
    last_reg_num = 0
    in_schedules = False

    for idx, (p_num, line) in enumerate(doc_lines):
        s = line.strip()
        prev_line = doc_lines[idx - 1][1].strip() if idx > 0 else ""

        m_head = reg_heading_pattern.match(s)
        m_inline = reg_inline_pattern.match(s)
        match = m_head or m_inline

        is_heading = False
        name = None
        inline_body = ""

        if match:
            reg_num_str = match.group(1)
            sub_num = match.group(2)
            sched_num = match.group(3)

            if sched_num:
                in_schedules = True
                is_heading = True
                name = sched_num.upper()
            elif reg_num_str and not in_schedules:
                reg_num = int(reg_num_str)
                continuing_prepositions = ("under", "to", "of", "in", "the", "and", "or", "with", "that", "from", "for")
                is_cont = any(prev_line.lower().endswith(f" {prep}") or prev_line.lower() == prep for prep in continuing_prepositions)

                if (reg_num == last_reg_num + 1 or (last_reg_num == 0 and reg_num == 1)) and not is_cont:
                    is_heading = True
                    last_reg_num = reg_num
                    if sub_num:
                        name = f"Regulation {reg_num}({sub_num})"
                    else:
                        name = f"Regulation {reg_num}"
            elif reg_num_str and in_schedules:
                is_heading = True
                name = f"Item {reg_num_str}"

            if is_heading:
                inline_body = match.group(4) if m_inline else ""

        if is_heading:
            if current_clause and current_clause["lines"]:
                clause_text = "\n".join(current_clause["lines"]).strip()
                if len(clause_text) >= min_clause_length:
                    clauses.append(
                        SegmentedClause(
                            clause_number=current_clause["name"],
                            text=clause_text,
                            start_page=current_clause["start_page"],
                            end_page=p_num,
                            char_start=0,
                            char_end=len(clause_text),
                        )
                    )

            current_clause = {
                "name": name,
                "start_page": p_num,
                "lines": [inline_body] if inline_body else []
            }
        elif current_clause is not None:
            current_clause["lines"].append(line)

    if current_clause and current_clause["lines"]:
        last_page = doc_lines[-1][0] if doc_lines else 1
        clause_text = "\n".join(current_clause["lines"]).strip()
        if len(clause_text) >= min_clause_length:
            clauses.append(
                SegmentedClause(
                    clause_number=current_clause["name"],
                    text=clause_text,
                    start_page=current_clause["start_page"],
                    end_page=last_page,
                    char_start=0,
                    char_end=len(clause_text),
                )
            )

    return clauses

if __name__ == "__main__":
    doc = fitz.open("backend/data/raw_sources/2494-47_E.pdf")
    pages = [doc[i].get_text() for i in range(len(doc))]
    meta = extract_document_preamble(pages)
    print("EXTRACTED PREAMBLE METADATA:", meta)
    clauses = segment_document_clauses(pages)
    print(f"EXTRACTED CLAUSES: {len(clauses)}")
    for c in clauses[:10]:
        print(f"  {c.clause_number} (p.{c.start_page}-{c.end_page}): {len(c.text)} chars | {repr(c.text[:60])}")
