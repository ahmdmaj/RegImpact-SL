import re
import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
p1 = doc[0].get_text()

patterns = [
    re.compile(
        r"^\s*((?:Regulation|Section|Article|Schedule|Rule|Clause|Item|Part)\s+\d+(?:\.\d+)*(?:\s+Part\s+[A-Z]\s+Item\s+\d+)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(\d+\.(?:\s*\(\d+\))?)\s+[A-Z]",
    ),
]

for idx, line in enumerate(p1.split("\n")):
    for p in patterns:
        m = p.search(line)
        if m:
            print(f"Line {idx}: {repr(m.group(1))} -> {repr(line[:60])}")
            break
