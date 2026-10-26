import sys
import hashlib
from pathlib import Path
import fitz

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import SourceDocumentORM, ClauseORM

raw_dir = Path("backend/data/raw_sources")

def inspect_one(key, filename, doc_id):
    filepath = raw_dir / filename
    print("=" * 80)
    print(f"CANDIDATE: {key} -> {filename}")
    print(f"Size: {filepath.stat().st_size} bytes | SHA-256: {hashlib.sha256(filepath.read_bytes()).hexdigest()}")
    
    doc = fitz.open(str(filepath))
    print(f"Total Pages: {len(doc)}")
    
    for p_idx in range(len(doc)):
        txt = doc[p_idx].get_text()
        print(f"\n--- PAGE {p_idx + 1} ({len(txt)} chars) ---")
        lines = [line.strip() for line in txt.split("\n") if line.strip()]
        for l in lines[:15]:
            print("  ", l)
        if len(lines) > 15:
            print(f"   ... [{len(lines)-15} more lines] ...")
            print("   LAST 5 LINES:")
            for l in lines[-5:]:
                print("  ", l)

    with session_scope() as db:
        doc_orm = db.query(SourceDocumentORM).filter_by(id=doc_id).first()
        if doc_orm:
            print(f"\nDB Record: ID={doc_orm.id}")
            print(f"  Title: {doc_orm.title}")
            print(f"  Authority: {doc_orm.authority}")
            print(f"  Gazette No: {doc_orm.gazette_no}")
            print(f"  Pub Date: {doc_orm.publication_date}")
            print(f"  Synthetic: {doc_orm.is_synthetic}")
            clauses = db.query(ClauseORM).filter_by(document_id=doc_id).all()
            print(f"  Clauses ({len(clauses)}):")
            for c in clauses:
                print(f"    - ID: {c.clause_id} | Num: {c.clause_number} | Pages: {c.start_page}-{c.end_page} | EmbVerified: {c.embedding_verified}")
                print(f"      Text: {c.text[:100]}...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "2494-06_E"
        
    mapping = {
        "2494-06_E": ("2494-06_E.pdf", "doc_15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b"),
        "colouring_2011": ("food_amendment_colouring_substances_regulations_2011_en.pdf", "doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7"),
        "preservative": ("preservative-english.pdf", "doc_3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f"),
        "flavouring_2013": ("food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf", "doc_b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a"),
    }
    fn, did = mapping[target]
    inspect_one(target, fn, did)
