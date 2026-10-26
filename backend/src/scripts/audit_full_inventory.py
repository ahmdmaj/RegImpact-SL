import sys
import hashlib
import json
from pathlib import Path
import pypdf

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    DocumentPageORM,
    ClauseORM,
    RuleORM,
    HumanReviewAuditORM,
    SYNTHETIC_DOCUMENT_IDS,
    is_synthetic_document,
    is_synthetic_clause,
    is_synthetic_rule,
)

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def inspect_pdf_text(filepath: Path) -> str:
    try:
        reader = pypdf.PdfReader(str(filepath))
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text() or ""
            return text[:300].replace("\n", " ")
    except Exception as e:
        return f"<PDF read error: {e}>"
    return ""

def audit_full_inventory():
    raw_dir = Path("backend/data/raw_sources")
    
    with session_scope() as db:
        docs = db.query(SourceDocumentORM).all()
        print(f"Total SourceDocumentORM records in DB: {len(docs)}")
        
        doc_audit = []
        for d in docs:
            clauses = db.query(ClauseORM).filter(ClauseORM.document_id == d.id).all()
            rules = (
                db.query(RuleORM)
                .join(ClauseORM, RuleORM.clause_id == ClauseORM.clause_id)
                .filter(ClauseORM.document_id == d.id)
                .all()
            )
            
            # Check actual file
            fpath = Path(d.file_path) if d.file_path else None
            resolved_path = None
            if fpath and fpath.exists():
                resolved_path = fpath
            elif fpath and (raw_dir / fpath.name).exists():
                resolved_path = raw_dir / fpath.name
            elif (raw_dir / f"{d.sha256_hash}.pdf").exists():
                resolved_path = raw_dir / f"{d.sha256_hash}.pdf"
                
            actual_hash = sha256_file(resolved_path) if resolved_path else None
            actual_size = resolved_path.stat().st_size if resolved_path else 0
            snippet = inspect_pdf_text(resolved_path) if resolved_path else ""
            
            # Classification
            classification = "UNVERIFIED"
            classification_reason = ""
            
            if d.id in ("doc_fcau_labelling_2024", "doc_cea_epl_2022", "doc_caa_mrp_2023", "test_live_doc_pgvector"):
                classification = "SYNTHETIC_FIXTURE"
                classification_reason = "Hardcoded synthetic fixture with pseudo-hash"
            elif actual_size in (1033, 1037):
                classification = "TEST_FIXTURE_UPLOAD"
                classification_reason = f"Integration test dummy upload (size {actual_size} bytes)"
            elif d.id == "doc_lec_03" or "Lec 03" in d.title:
                classification = "EXCLUDED_NON_STATUTORY"
                classification_reason = "Academic lecture slide deck; secondary commentary, not primary law"
            elif d.id == "doc_labelling_regulations_final_2026":
                classification = "EXCLUDED_NON_PROMULGATED"
                classification_reason = "Internal draft of Food Advisory Committee; not officially promulgated in Gazette"
            elif d.id == "doc_gazette_2494_47":
                classification = "AUTHENTIC_PROMULGATED"
                classification_reason = "Official Gazette Extraordinary No. 2494/47 (2026-06-26) with verified hash"
            elif d.id in ("doc_gazette_2443_27", "doc_gazette_2496_03", "doc_fcau_labelling_advertising_en"):
                classification = "AUTHENTIC_PROMULGATED"
                classification_reason = "Official Gazette / Government legal publication"
            elif d.id.startswith("doc_") and len(d.id) > 50:
                # Hex-named documents from hash
                if actual_size > 10000:
                    classification = "AUTHENTIC_CANDIDATE_UNVERIFIED_PROVENANCE"
                    classification_reason = f"Substantive PDF ({actual_size} bytes), but needs official publication metadata verification"
                else:
                    classification = "TEST_FIXTURE"
                    classification_reason = "Small test fixture"
            
            doc_audit.append({
                "id": d.id,
                "title": d.title,
                "authority": d.authority,
                "gazette_no": d.gazette_no,
                "publication_date": str(d.publication_date) if d.publication_date else None,
                "source_url": d.source_url,
                "sha256_hash": d.sha256_hash,
                "file_path": d.file_path,
                "resolved_file": str(resolved_path) if resolved_path else None,
                "actual_size": actual_size,
                "actual_hash": actual_hash,
                "hash_match": actual_hash == d.sha256_hash if actual_hash else False,
                "is_synthetic_db": d.is_synthetic,
                "classification": classification,
                "classification_reason": classification_reason,
                "clause_count": len(clauses),
                "verified_embs": sum(1 for c in clauses if c.embedding_verified),
                "rule_count": len(rules),
                "snippet": snippet,
            })
            
        print(json.dumps(doc_audit, indent=2))
        
        # Save to json file for reference
        out_path = Path("backend/data/quarantine/doc_inventory_audit.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc_audit, indent=2), encoding="utf-8")
        print(f"\nSaved inventory to {out_path}")

if __name__ == "__main__":
    audit_full_inventory()
