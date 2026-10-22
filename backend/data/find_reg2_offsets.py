import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
p1_text = doc[0].get_text()

reg2_start = p1_text.find("2. A person shall not import")
reg3_start = p1_text.find("3. (1)")

print(f"p1 length: {len(p1_text)}")
print(f"Reg 2 start: {reg2_start}")
print(f"Reg 3 start: {reg3_start}")

reg2_text = p1_text[reg2_start:reg3_start].strip()
print("=== REGULATION 2 TEXT ===")
print(reg2_text)
print(f"Length of Reg 2: {len(reg2_text)}")
