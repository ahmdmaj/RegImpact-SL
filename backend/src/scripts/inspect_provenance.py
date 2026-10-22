"""Inspection script to verify provenance and extract text from candidate raw PDFs."""
import hashlib
import os
from pathlib import Path
import pymupdf

RAW_DIR = Path("backend/data/raw_sources")
candidates = [
    "2443-27_E.pdf",
    "Labelling_Regulations_Final_-_11.02.2026.pdf",
    "English_The_Food_Labelling_and_Advertising_Regulations.pdf",
    "preservative-english.pdf",
    "food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf",
    "food_amendment_colouring_substances_regulations_2011_en.pdf",
    "2494-06_E.pdf",
    "2494-47_E.pdf",
    "2496-03_E.pdf",
]

for name in candidates:
    p = RAW_DIR / name
    if not p.exists():
        print(f"MISSING: {name}")
        continue
    data = p.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    doc = pymupdf.open(str(p))
    print("=" * 80)
    print(f"FILE: {name}")
    print(f"SIZE: {len(data)} bytes | PAGES: {len(doc)} | SHA-256: {h}")
    # Inspect page 1 and page 2 text
    for page_idx in range(min(2, len(doc))):
        text = doc[page_idx].get_text()
        first_few_lines = "\n".join(text.splitlines()[:15])
        print(f"--- PAGE {page_idx + 1} (chars: {len(text)}) ---")
        print(first_few_lines)
    doc.close()
