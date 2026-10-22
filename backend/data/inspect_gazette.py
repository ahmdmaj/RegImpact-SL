import pymupdf

def inspect_doc(filename, max_pages=4):
    p = "/app/backend/data/raw_sources/" + filename
    doc = pymupdf.open(p)
    print(f"=== {filename} ===")
    for idx in range(min(max_pages, len(doc))):
        print(f"--- PAGE {idx + 1} ---")
        print(doc[idx].get_text())

inspect_doc("2494-47_E.pdf", 4)
