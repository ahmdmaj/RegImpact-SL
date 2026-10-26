import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import fitz

doc = fitz.open("backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf")
print("=== PAGE 2 (FULL) ===")
print(doc[1].get_text())
print("\n=== PAGE 3 (FIRST 1000 CHARS) ===")
print(doc[2].get_text()[:1000])
