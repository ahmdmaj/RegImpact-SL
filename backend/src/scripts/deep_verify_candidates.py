import sys
import hashlib
from pathlib import Path
import fitz  # PyMuPDF

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import SourceDocumentORM, ClauseORM

raw_dir = Path("backend/data/raw_sources")

candidates = [
    {
        "key": "2494-06_E",
        "file": raw_dir / "2494-06_E.pdf",
        "doc_id": "doc_15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b"
    },
    {
        "key": "colouring_2011",
        "file": raw_dir / "food_amendment_colouring_substances_regulations_2011_en.pdf",
        "doc_id": "doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7"
    },
    {
        "key": "preservative",
        "file": raw_dir / "preservative-english.pdf",
        "doc_id": "doc_3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f"
    },
    {
        "key": "flavouring_2013",
        "file": raw_dir / "food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf",
        "doc_id": "doc_b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a"
    }
]

def analyze_pdf(c):
    filepath = c["file"]
    print("=" * 80)
    print(f"CANDIDATE: {c['key']} -> {filepath.name}")
    print(f"File size: {filepath.stat().st_size} bytes")
    h = hashlib.sha256(filepath.read_bytes()).hexdigest()
    print(f"SHA-256: {h}")
    
    doc = fitz.open(str(filepath))
    print(f"Page count: {len(doc)}")
    
    for p_num in range(len(doc)):
        p_text = doc[p_num].get_text()
        print(f"\n--- PAGE {p_num + 1} FULL TEXT ({len(p_text)} chars) ---")
        print(p_text.strip())
        
    # Check database document and clauses
    with session_scope() as db:
        doc_orm = db.query(SourceDocumentORM).filter_by(id=c["doc_id"]).first()
        if doc_orm:
            print(f"\nDatabase Record: ID={doc_orm.id}")
            print(f"  Title: {doc_orm.title}")
            print(f"  Authority: {doc_orm.authority}")
            print(f"  Gazette No: {doc_orm.gazette_no}")
            print(f"  Pub Date: {doc_orm.publication_date}")
            print(f"  Source URL: {doc_orm.source_url}")
            print(f"  Is Synthetic: {doc_orm.is_synthetic}")
            
            clauses = db.query(ClauseORM).filter_by(document_id=c["doc_id"]).all()
            print(f"  Clauses in DB ({len(clauses)}):")
            for cl in clauses:
                print(f"    - Clause ID: {cl.clause_id} | Num: {cl.clause_number} | Pages: {cl.start_page}-{cl.end_page} | verified_emb: {cl.embedding_verified}")
                print(f"      Valid: {cl.valid_from} to {cl.valid_to} | Transition: {cl.transition_until} | Superseded by: {cl.superseded_by_clause_id}")
                print(f"      Text: {cl.text[:120]}...")
        else:
            print(f"\nNo DB record found for {c['doc_id']}")

def main():
    for c in candidates:
        analyze_pdf(c)

if __name__ == "__main__":
    main()
