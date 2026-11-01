import json
import os
import fitz

with open("/app/backend/data/inventory_output.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

inventory = raw_data["inventory"]
db_records = raw_data["database_records"]

# Build lookup by SHA-256
by_sha = {}
for item in inventory:
    by_sha.setdefault(item["sha256"], []).append(item)

# Build DB lookup by SHA-256
db_by_sha = {r["sha256"]: r for r in db_records}

# Categorize unique SHA-256 items
categories = {
    "authentic_gazettes": [],
    "drafts_and_academic": [],
    "test_fixtures": []
}

for sha, file_list in by_sha.items():
    primary = file_list[0]
    filenames = [f["filename"] for f in file_list]
    paths = [f["path"] for f in file_list]
    
    # Extract more text to be 100% accurate on classification
    full_path = "/app/" + primary["path"] if not primary["path"].startswith("/") else primary["path"]
    full_text = ""
    try:
        doc = fitz.open(full_path)
        for i in range(min(5, len(doc))):
            full_text += doc[i].get_text() + "\n"
        doc.close()
    except Exception as e:
        full_text = primary.get("text_sample", "")

    # Check for authentic Gazette indicators
    is_authentic_gazette = False
    gazette_no = primary.get("gazette_number")
    gazette_date = primary.get("gazette_date")
    reg_title = primary.get("reg_title")
    lang = primary.get("language")
    
    if any(k in full_text.lower() for k in [
        "the gazette of the democratic socialist republic of sri lanka",
        "extraordinary",
        "part i : sec",
        "ශ්‍රී ලංකා ප්‍රජාතාන්ත්‍රික සමාජවාදී ජනරජයේ ගැසට් පත්‍රය",
        "இலங்கை சனநாயக சோசலிசக் குடியரசு வர்த்தமானப் பத்திரிகை"
    ]):
        is_authentic_gazette = True

    # Refine classification
    if any(fn.lower() in ["lec 03.pdf", "regimpact final plan.pdf"] or "lecture" in full_text.lower() or "final plan" in fn.lower() for fn in filenames):
        cat = "drafts_and_academic"
    elif any("test" in fn.lower() or "cold storage" in full_text.lower() or "e2e" in fn.lower() for fn in filenames) and primary["size_bytes"] < 5000:
        cat = "test_fixtures"
    elif "draft" in full_text.lower() or "draft" in str(reg_title).lower() or any("draft" in fn.lower() or "fac final" in full_text.lower() for fn in filenames):
        cat = "drafts_and_academic"
    elif is_authentic_gazette or gazette_no:
        cat = "authentic_gazettes"
    else:
        cat = "test_fixtures" if primary["size_bytes"] < 10000 else "drafts_and_academic"

    # In DB?
    in_db = sha in db_by_sha
    db_info = db_by_sha.get(sha)

    entry = {
        "sha256": sha,
        "filenames": filenames,
        "primary_filename": filenames[0],
        "paths": paths,
        "file_count": len(file_list),
        "size_bytes": primary["size_bytes"],
        "page_count": primary["page_count"],
        "category": cat,
        "gazette_number": gazette_no,
        "gazette_date": gazette_date,
        "reg_title": reg_title,
        "language": lang,
        "registered_in_db": in_db,
        "db_id": db_info["id"] if db_info else None,
        "db_title": db_info["title"] if db_info else None,
        "db_clause_count": db_info["clause_count"] if db_info else None,
        "db_status": db_info["extraction_status"] if db_info else None,
        "text_preview": full_text[:300].replace("\n", " ").strip()
    }
    categories[cat].append(entry)

print("=== DETAILED INVENTORY BREAKDOWN ===")
print(f"Total Unique Document Hashes: {len(by_sha)}")
print(f"  - Authentic Gazettes: {len(categories['authentic_gazettes'])}")
print(f"  - Drafts & Academic / Plan Documents: {len(categories['drafts_and_academic'])}")
print(f"  - Test Fixtures / Synthetic Uploads: {len(categories['test_fixtures'])}")

print("\n--- AUTHENTIC GAZETTES FOUND ---")
for g in sorted(categories["authentic_gazettes"], key=lambda x: str(x["gazette_number"])):
    print(f"\nGazette No: {g['gazette_number']} | Date: {g['gazette_date']}")
    print(f"  Title: {g['reg_title']}")
    print(f"  Language: {g['language']} | Pages: {g['page_count']} | Size: {g['size_bytes']} bytes")
    print(f"  SHA-256: {g['sha256']}")
    print(f"  Filenames ({g['file_count']}): {g['filenames']}")
    print(f"  DB Registered: {g['registered_in_db']} (ID: {g['db_id']}, Clauses: {g['db_clause_count']})")
    print(f"  Preview: {g['text_preview'][:150]}...")

print("\n--- DRAFTS & ACADEMIC DOCUMENTS ---")
for d in categories["drafts_and_academic"]:
    print(f"\nTitle: {d['reg_title'] or d['primary_filename']}")
    print(f"  Pages: {d['page_count']} | Size: {d['size_bytes']} bytes | Language: {d['language']}")
    print(f"  SHA-256: {d['sha256']}")
    print(f"  Filenames: {d['filenames']}")
    print(f"  DB Registered: {d['registered_in_db']} (ID: {d['db_id']})")

print(f"\n--- TEST FIXTURES / SYNTHETIC COLD STORAGE UPLOADS ---")
print(f"Count: {len(categories['test_fixtures'])} unique hashes")
print(f"Sample test fixture filenames: {[f['primary_filename'] for f in categories['test_fixtures'][:10]]}")

# Save detailed breakdown
with open("/app/backend/data/detailed_inventory_breakdown.json", "w", encoding="utf-8") as f:
    json.dump({
        "summary": {
            "total_files": len(inventory),
            "total_unique_hashes": len(by_sha),
            "authentic_gazettes_count": len(categories["authentic_gazettes"]),
            "drafts_count": len(categories["drafts_and_academic"]),
            "test_fixtures_count": len(categories["test_fixtures"])
        },
        "authentic_gazettes": categories["authentic_gazettes"],
        "drafts_and_academic": categories["drafts_and_academic"],
        "test_fixtures": categories["test_fixtures"]
    }, f, indent=2, ensure_ascii=False)

print("\nSaved to /app/backend/data/detailed_inventory_breakdown.json")

