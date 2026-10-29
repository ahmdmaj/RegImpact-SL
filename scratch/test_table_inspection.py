import pymupdf
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

doc = pymupdf.open('backend/data/raw_sources/2494-06_E.pdf')
for i, page in enumerate(doc):
    tables = page.find_tables()
    print(f"=== Page {i+1} Tables: {len(tables.tables)} ===")
    for idx, t in enumerate(tables):
        data = t.extract()
        print(f"  Table #{idx+1} bbox: {t.bbox}")
        for r_idx, row in enumerate(data):
            clean_row = [str(c).replace('\n', ' ') if c else '' for c in row]
            print(f"    Row {r_idx}: {clean_row}")
