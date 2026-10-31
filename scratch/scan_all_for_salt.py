import sys
import os
import pymupdf
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

scan_dirs = [
    r"C:\Users\HP\Desktop\PROJECTS\RegImpact-SL\backend\data\raw_sources",
    r"C:\Users\HP\Downloads",
    r"C:\Users\HP\Desktop",
]

print("Scanning for salt or 2494/48 across candidate folders...")
found_any = False

for d in scan_dirs:
    if not os.path.exists(d):
        continue
    for fname in os.listdir(d):
        if not fname.lower().endswith(".pdf"):
            continue
        full_path = os.path.join(d, fname)
        try:
            doc = pymupdf.open(full_path)
            for i, page in enumerate(doc):
                txt = page.get_text("text").lower()
                if "2494/48" in txt or "iodiz" in txt or "iodization of salt" in txt:
                    print(f"MATCH FOUND: {full_path} on page {i+1}")
                    found_any = True
                    break
        except Exception as e:
            pass

if not found_any:
    print("NO files matching '2494/48' or 'iodiz' or 'iodization of salt' found in any scanned folder.")

