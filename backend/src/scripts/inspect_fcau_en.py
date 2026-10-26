import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import fitz

doc = fitz.open("backend/data/raw_sources/English_The_Food_Labelling_and_Advertising_Regulations.pdf")
print("=== English_The_Food_Labelling_and_Advertising_Regulations.pdf ===")
print("Pages:", len(doc))
print("Page 1 snippet:")
print(doc[0].get_text()[:1200])
