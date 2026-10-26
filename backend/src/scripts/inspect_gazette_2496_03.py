import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import fitz

doc = fitz.open("backend/data/raw_sources/2496-03_E.pdf")
print("=== Gazette 2496/03 ===")
print("Pages:", len(doc))
print("Page 1 snippet:")
print(doc[0].get_text()[:1200])
