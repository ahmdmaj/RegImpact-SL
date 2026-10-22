import hashlib
from pathlib import Path
import pymupdf

RAW_DIR = Path("/app/backend/data/raw_sources")
files = [
    "2443-27_E.pdf",
    "Labelling_Regulations_Final_-_11.02.2026.pdf",
    "English_The_Food_Labelling_and_Advertising_Regulations.pdf",
    "2494-47_E.pdf",
]

for name in files:
    p = RAW_DIR / name
    if not p.exists():
        print(f"MISSING: {p}")
        continue
    data = p.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    doc = pymupdf.open(str(p))
    print("=" * 80)
    print(f"FILE: {name}")
    print(f"SIZE: {len(data)} bytes | PAGES: {len(doc)} | SHA-256: {h}")
    for i in range(min(3, len(doc))):
        print(f"--- PAGE {i + 1} (chars: {len(doc[i].get_text())}) ---")
        print(doc[i].get_text()[:600])
    doc.close()
