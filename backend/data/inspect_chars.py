import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/2494-47_E.pdf")
p1 = doc[0].get_text()
for char in set(p1):
    if ord(char) > 127 and ord(char) < 0x0D80: # not Sinhala
        print(f"Special char: U+{ord(char):04X} ({repr(char)})")
