import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
p1 = doc[0].get_text()
for char in sorted(set(p1)):
    if ord(char) > 127:
        print(f"Char: U+{ord(char):04X} ({repr(char)})")
print("\n--- Snippet of p1 ---")
print(p1[:500])
