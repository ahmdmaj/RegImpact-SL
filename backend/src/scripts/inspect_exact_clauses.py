import sys
from pathlib import Path
import fitz

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

raw_dir = Path("backend/data/raw_sources")

def inspect_sugar():
    print("=" * 80)
    print("SOURCE: 2494-06_E.pdf (Gazette 2494/06 - Sugar Colour Coding)")
    doc = fitz.open(str(raw_dir / "2494-06_E.pdf"))
    for i, page in enumerate(doc):
        print(f"\n--- PAGE {i+1} ---")
        print(page.get_text())

def inspect_preservatives():
    print("=" * 80)
    print("SOURCE: preservative-english.pdf (Gazette 2113/16 - Food Preservatives 2019)")
    doc = fitz.open(str(raw_dir / "preservative-english.pdf"))
    for i in range(min(5, len(doc))):
        print(f"\n--- PAGE {i+1} ---")
        print(doc[i].get_text())

def inspect_flavourings():
    print("=" * 80)
    print("SOURCE: food_flavouring_..._2013_en.pdf (Gazette 1795/51 - Food Flavouring 2013)")
    doc = fitz.open(str(raw_dir / "food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf"))
    for i, page in enumerate(doc):
        print(f"\n--- PAGE {i+1} ---")
        print(page.get_text())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "sugar":
            inspect_sugar()
        elif cmd == "preservatives":
            inspect_preservatives()
        elif cmd == "flavourings":
            inspect_flavourings()
    else:
        inspect_sugar()
        inspect_preservatives()
        inspect_flavourings()
