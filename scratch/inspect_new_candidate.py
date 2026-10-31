import sys
import pymupdf
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

path = r"backend/data/raw_sources/2494-06_E_1784568259.pdf"

with open(path, "rb") as f:
    data = f.read()

sha256 = hashlib.sha256(data).hexdigest()
print(f"File Path: {path}")
print(f"File Size: {len(data)} bytes")
print(f"SHA-256: {sha256}")

doc = pymupdf.open(path)
print(f"Page Count: {len(doc)}")
print(f"Metadata: {doc.metadata}")

print("\n" + "="*80)
for i in range(len(doc)):
    print(f"--- PAGE {i+1} ---")
    print(doc[i].get_text("text"))
    print("="*80)
