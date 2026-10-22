import pymupdf

p = "/app/backend/data/raw_sources/2443-27_E.pdf"
doc = pymupdf.open(p)
print("=== 2443-27_E.pdf PAGE 1 ===")
print(doc[0].get_text())
