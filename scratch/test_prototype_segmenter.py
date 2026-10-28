import fitz
import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

doc = fitz.open('backend/data/raw_sources/2494-47_E.pdf')
pages_data = [(i + 1, doc[i].get_text()) for i in range(len(doc))]

header_patterns = [
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

def is_header_or_footer(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(p.match(s) for p in header_patterns)

# A heading line strictly starts with:
# 1. or 1. (1) or Regulation 1. or SCHEDULE I
reg_heading_pattern = re.compile(
    r'^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]+))\s*$',
    re.IGNORECASE
)
reg_inline_pattern = re.compile(
    r'^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]+))\s+([A-Z].*)',
    re.IGNORECASE
)

# Preamble extraction
preamble_lines = []
doc_lines = []
in_regulations = False
for p_num, p_text in pages_data:
    for line in p_text.split('\n'):
        if is_header_or_footer(line):
            continue
        if line.strip() == 'REGULATIONS':
            in_regulations = True
            continue
        if not in_regulations:
            preamble_lines.append(line)
        else:
            doc_lines.append((p_num, line))

clauses = []
current_clause = None

for p_num, line in doc_lines:
    s = line.strip()
    m_head = reg_heading_pattern.match(s)
    m_inline = reg_inline_pattern.match(s)
    match = m_head or m_inline
    
    if match:
        reg_num = match.group(1)
        sub_num = match.group(2)
        sched_num = match.group(3)
        if sched_num:
            name = sched_num.upper()
        elif sub_num:
            name = f'Regulation {reg_num}({sub_num})'
        else:
            name = f'Regulation {reg_num}'
            
        if current_clause:
            current_clause['end_page'] = p_num
            clauses.append(current_clause)
            
        inline_body = match.group(4) if m_inline else ''
        current_clause = {
            'name': name,
            'start_page': p_num,
            'lines': [inline_body] if inline_body else []
        }
    elif current_clause is not None:
        current_clause['lines'].append(line)

if current_clause:
    current_clause['end_page'] = pages_data[-1][0]
    clauses.append(current_clause)

print("=== PREAMBLE EXTRACTED ===")
preamble_text = " ".join(l.strip() for l in preamble_lines if l.strip())
print(f"Preamble length: {len(preamble_text)} chars")
print(f"Snippet: {preamble_text[:250]}...")

print(f"\nTotal Clauses Discovered: {len(clauses)}")
for i, c in enumerate(clauses[:10], 1):
    text = ' '.join(l.strip() for l in c['lines'] if l.strip())
    print(f"[{i:02d}] {c['name']} (Pages {c['start_page']}-{c['end_page']}): {len(text)} chars | Excerpt: {text[:80]}...")
