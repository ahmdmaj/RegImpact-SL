import sys
import pymupdf
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

p1 = r"backend/data/raw_sources/2494-06_E.pdf"
p2 = r"backend/data/raw_sources/2494-06_E_1784568259.pdf"

with open(p1, "rb") as f:
    d1 = f.read()
with open(p2, "rb") as f:
    d2 = f.read()

print("File 1 (2494-06_E.pdf):")
print("  Size:", len(d1))
print("  SHA256:", hashlib.sha256(d1).hexdigest())

print("File 2 (2494-06_E_1784568259.pdf):")
print("  Size:", len(d2))
print("  SHA256:", hashlib.sha256(d2).hexdigest())

doc1 = pymupdf.open(p1)
doc2 = pymupdf.open(p2)

print("\nDoc 1 Page 1 text snippet:")
print(doc1[0].get_text("text")[:300])

print("\nDoc 2 Page 1 text snippet:")
print(doc2[0].get_text("text")[:300])
