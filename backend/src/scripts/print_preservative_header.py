import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import fitz

doc = fitz.open("backend/data/raw_sources/preservative-english.pdf")
print("=== PAGE 1 ===")
print(doc[0].get_text()[:1500])
print("\n=== PAGE 2 ===")
print(doc[1].get_text()[:1500])
