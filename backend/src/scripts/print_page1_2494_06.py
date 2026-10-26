import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import fitz
doc = fitz.open("backend/data/raw_sources/2494-06_E.pdf")
print("=== PAGE 1 ===")
print(doc[0].get_text())

