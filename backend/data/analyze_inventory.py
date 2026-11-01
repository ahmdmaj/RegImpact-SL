import json
from collections import defaultdict

with open("/app/backend/data/inventory_output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

inventory = data["inventory"]
db_records = data["database_records"]

print(f"=== INVENTORY SUMMARY ===")
print(f"Total PDFs: {len(inventory)}")
print(f"Total DB Records: {len(db_records)}")

# Group by SHA-256
by_hash = defaultdict(list)
for item in inventory:
    by_hash[item["sha256"]].append(item)

print(f"\nUnique SHA-256 hashes among PDFs: {len(by_hash)}")

# Report duplicate sets
dup_count = 0
for h, files in by_hash.items():
    if len(files) > 1:
        dup_count += 1
        print(f"\n[DUPLICATE SET {dup_count}] SHA256: {h[:16]}... ({len(files)} files)")
        for f in files:
            print(f"  - {f['filename']} ({f['path']}) | Size: {f['size_bytes']} bytes | Pages: {f['page_count']}")

# Check Gazette identification
gazettes = defaultdict(list)
non_gazettes = []
for item in inventory:
    gno = item.get("gazette_number")
    if gno:
        gazettes[gno].append(item)
    else:
        non_gazettes.append(item)

print(f"\n=== GAZETTE IDENTIFICATION ===")
for gno, files in sorted(gazettes.items()):
    sample = files[0]
    print(f"\nGazette No: {gno} ({len(files)} files)")
    print(f"  Title: {sample['reg_title']}")
    print(f"  Date: {sample['gazette_date']}")
    print(f"  Language: {sample['language']}")
    print(f"  Distinct SHA256s: {len(set(f['sha256'] for f in files))}")
    for f in files[:5]:
        print(f"    * {f['filename']} (Size: {f['size_bytes']}, Pages: {f['page_count']}, SHA: {f['sha256'][:8]}...)")
    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more files")

# Specifically search for 2494/48, Salt, Iodiz in all PDFs
print(f"\n=== GAZETTE 2494/48 / IODIZATION OF SALT VERIFICATION ===")
found_candidates = []
for item in inventory:
    text_sample = item.get("text_sample", "").lower()
    fn = item.get("filename", "").lower()
    gno = str(item.get("gazette_number") or "").lower()
    title = str(item.get("reg_title") or "").lower()
    
    if "48" in gno or "2494/48" in gno or "2494-48" in fn or "salt" in text_sample or "iodiz" in text_sample or "salt" in fn or "iodiz" in fn or "salt" in title:
        found_candidates.append(item)

print(f"Found {len(found_candidates)} potential candidate files related to 2494/48 or Salt:")
for c in found_candidates:
    print(f"  - Filename: {c['filename']}")
    print(f"    Path: {c['path']}")
    print(f"    Gazette No: {c['gazette_number']} | Date: {c['gazette_date']}")
    print(f"    Title: {c['reg_title']} | Language: {c['language']}")
    print(f"    Size: {c['size_bytes']} bytes | Pages: {c['page_count']} | SHA256: {c['sha256']}")
    print(f"    Sample: {c['text_sample'][:150]}...")

# Compare DB vs Local Files
print(f"\n=== DATABASE VS LOCAL FILES RECONCILIATION ===")
db_by_hash = {r["sha256"]: r for r in db_records}
db_by_path = {r["file_path"]: r for r in db_records}
pdf_by_hash = by_hash

# 1. Registered in DB and present locally
both = []
db_missing_locally = []
for h, r in db_by_hash.items():
    if h in pdf_by_hash:
        both.append((r, pdf_by_hash[h]))
    else:
        db_missing_locally.append(r)

print(f"Documents registered in DB and present locally: {len(both)}")
for r, local_files in both:
    print(f"  - DB ID: {r['id']} | Title: {r['title']} | Clauses: {r['clause_count']} | Pages: {r['page_count']}")
    print(f"    Mapped local files ({len(local_files)}): {[f['filename'] for f in local_files]}")

print(f"\nDocuments registered in DB but missing locally: {len(db_missing_locally)}")
for r in db_missing_locally:
    print(f"  - DB ID: {r['id']} | Title: {r['title']} | Hash: {r['sha256']} | Path: {r['file_path']}")

# 2. Present locally but not in DB
local_not_in_db = []
for h, files in pdf_by_hash.items():
    if h not in db_by_hash:
        local_not_in_db.append(files)

print(f"\nUnique files present locally but NOT registered in DB: {len(local_not_in_db)}")
for files in local_not_in_db[:15]:
    f = files[0]
    print(f"  - Filename: {f['filename']} (x{len(files)}) | Pages: {f['page_count']} | Type: {f['document_type']} | Title: {f['reg_title']} | GazNo: {f['gazette_number']}")
if len(local_not_in_db) > 15:
    print(f"  ... and {len(local_not_in_db) - 15} more unique local files")

# Output complete analysis to JSON
with open("/app/backend/data/inventory_analysis.json", "w", encoding="utf-8") as f:
    json.dump({
        "total_pdfs": len(inventory),
        "total_unique_hashes": len(by_hash),
        "duplicate_sets": [{"hash": h, "files": [f["path"] for f in files]} for h, files in by_hash.items() if len(files) > 1],
        "gazette_groups": {gno: [{"filename": f["filename"], "hash": f["sha256"], "pages": f["page_count"]} for f in files] for gno, files in gazettes.items()},
        "candidates_for_2494_48": found_candidates,
        "db_matched": [{"db_id": r["id"], "title": r["title"], "hash": r["sha256"], "local_count": len(local_files)} for r, local_files in both],
        "db_missing_locally": db_missing_locally,
        "local_not_in_db_sample": [{"filename": f[0]["filename"], "count": len(f), "hash": f[0]["sha256"], "type": f[0]["document_type"], "title": f[0]["reg_title"]} for f in local_not_in_db]
    }, f, indent=2, ensure_ascii=False)

print("\nAnalysis saved to /app/backend/data/inventory_analysis.json.")

