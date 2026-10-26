import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
import fitz

doc = fitz.open("backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf")
print("=== FLAVOURINGS PAGE 1 ===")
print(doc[0].get_text())
