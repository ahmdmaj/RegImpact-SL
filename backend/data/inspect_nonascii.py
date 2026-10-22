import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/2494-47_E.pdf")
p1 = doc[0].get_text()
for char in sorted(set(p1)):
    if ord(char) > 127:
        print(f"Char: U+{ord(char):04X} ({repr(char)})")
