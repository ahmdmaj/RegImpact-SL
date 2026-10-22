import pymupdf

p = "/app/backend/data/raw_sources/2494-47_E.pdf"
doc = pymupdf.open(p)
print("=== PAGE 1 ===")
print(doc[0].get_text())
print("=== PAGE 2 ===")
print(doc[1].get_text())
