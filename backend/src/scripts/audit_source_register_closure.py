import sys
import hashlib
import json
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    DocumentPageORM,
    ClauseORM,
    RuleORM,
    is_synthetic_document,
)

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    raw_dir = Path("backend/data/raw_sources")
    all_files = sorted([f for f in raw_dir.iterdir() if f.is_file() and f.name != ".gitkeep"])
    
    print(f"Total non-gitkeep files in {raw_dir}: {len(all_files)}")
    
    # Analyze by size and hash
    files_by_hash = {}
    files_by_size = {}
    file_records = []
    
    for f in all_files:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        h = sha256_file(f)
        
        file_records.append({
            "name": f.name,
            "size": size,
            "sha256": h,
            "mtime": mtime
        })
        
        files_by_hash.setdefault(h, []).append(f.name)
        files_by_size.setdefault(size, []).append(f.name)
        
    print(f"Unique SHA-256 hashes: {len(files_by_hash)}")
    print(f"Sizes distribution:")
    for sz in sorted(files_by_size.keys()):
        names = files_by_size[sz]
        print(f"  Size {sz} bytes: {len(names)} files")
        if len(names) <= 5:
            print(f"    -> {names}")
            
    print("\n--- Files with size 1033 or 1037 (Test fixtures) ---")
    test_fixture_files = [f for f in file_records if f["size"] in (1033, 1037)]
    print(f"Count: {len(test_fixture_files)}")
    
    print("\n--- Substantive files (size > 2000 bytes) ---")
    substantive_files = [f for f in file_records if f["size"] > 2000]
    print(f"Count: {len(substantive_files)}")
    for sf in substantive_files:
        print(f"  {sf['name']}: {sf['size']} bytes, hash={sf['sha256'][:16]}..., mtime={sf['mtime']}")
        
    # Check database records
    with session_scope() as db:
        docs = db.query(SourceDocumentORM).all()
        print(f"\n--- Total DB documents: {len(docs)} ---")
        for d in docs:
            clauses = db.query(ClauseORM).filter(ClauseORM.document_id == d.id).all()
            rules = (
                db.query(RuleORM)
                .join(ClauseORM, RuleORM.clause_id == ClauseORM.clause_id)
                .filter(ClauseORM.document_id == d.id)
                .all()
            )
            print(f"  ID: {d.id} | Title: {d.title[:35]} | synth={d.is_synthetic} | hash={d.sha256_hash[:16] if d.sha256_hash else 'None'} | clauses={len(clauses)} | rules={len(rules)}")

if __name__ == "__main__":
    main()
