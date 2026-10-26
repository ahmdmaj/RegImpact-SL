import fitz  # PyMuPDF

out = []

out.append("=== INSPECTING GAZETTE 1795/51 (Flavourings 2013) ===")
doc_flav = fitz.open("backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf")
out.append(f"Total pages: {len(doc_flav)}")

for p in range(len(doc_flav)):
    text = doc_flav[p].get_text()
    out.append(f"\n--- PAGE {p+1} FULL TEXT ---")
    out.append(text)

out.append("\n=== INSPECTING GAZETTE 2113/16 (Preservatives 2019) ===")
doc_pres = fitz.open("backend/data/raw_sources/preservative-english.pdf")
out.append(f"Total pages: {len(doc_pres)}")
for p in range(len(doc_pres)):
    text = doc_pres[p].get_text()
    if "3.1" in text or "jam" in text.lower():
        out.append(f"\n--- PAGE {p+1} TEXT (contains 3.1 / jam) ---")
        out.append(text)

with open("scratch/source_inspection_utf8.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("Successfully written scratch/source_inspection_utf8.txt")
