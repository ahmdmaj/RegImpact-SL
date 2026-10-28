"""Audit all PDFs in backend/data/raw_sources against PostgreSQL source_documents table."""
import os
import sys
import hashlib
from pathlib import Path

# Add project root
sys.path.insert(0, ".")

from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.db.models import SourceDocumentORM, ClauseORM

def audit_sources():
    raw_dir = Path("backend/data/raw_sources")
    pdf_files = list(raw_dir.glob("*.pdf"))
    
    db_url = "postgresql+psycopg://regimpact:regimpact@localhost:5432/regimpact"
    session = get_session_factory(create_engine_from_url(db_url))()
    
    db_docs = session.query(SourceDocumentORM).all()
    db_by_hash = {d.sha256_hash: d for d in db_docs if d.sha256_hash}
    db_by_id = {d.id: d for d in db_docs}
    
    print(f"Total PDFs in raw_sources: {len(pdf_files)}")
    print(f"Total SourceDocumentORM records in DB: {len(db_docs)}")
    
    print("\n--- OFFICIAL & SIZABLE REGULATORY SOURCE AUDIT ---")
    official_candidates = []
    for p in sorted(pdf_files, key=lambda f: f.stat().st_size, reverse=True):
        size = p.stat().st_size
        # Skip 1037-byte test dummy uploads
        if size == 1037:
            continue
        raw_bytes = p.read_bytes()
        sha = hashlib.sha256(raw_bytes).hexdigest()
        
        matched_doc = db_by_hash.get(sha) or db_by_id.get(p.stem) or db_by_id.get(f"doc_{p.stem}")
        clause_count = len(matched_doc.clauses) if matched_doc else 0
        
        print(f"File: {p.name} ({size} bytes)")
        print(f"  SHA256: {sha[:16]}...")
        if matched_doc:
            print(f"  Matched DB Doc ID: {matched_doc.id} | Title: {matched_doc.title[:45]} | Clauses in DB: {clause_count}")
        else:
            print(f"  Matched DB Doc ID: NONE (NOT IN DATABASE)")
            official_candidates.append(p)
            
    print(f"\nTotal non-dummy PDFs: {len([p for p in pdf_files if p.stat().st_size != 1037])}")
    print(f"Total completely unrepresented non-dummy PDFs: {len(official_candidates)}")
    
    session.close()

if __name__ == "__main__":
    audit_sources()
