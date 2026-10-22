import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
print("=== PAGE 1 ===")
print(doc[0].get_text())
