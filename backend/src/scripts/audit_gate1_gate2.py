import sys
import hashlib
import json
from pathlib import Path

sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    DocumentPageORM,
    ClauseORM,
    RuleORM,
    HumanReviewAuditORM,
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

def main():
    raw_dir = Path("backend/data/raw_sources")
    raw_files = list(raw_dir.glob("*"))
    print(f"=== RAW FILES ON DISK ({len(raw_files)}) ===")
    
    file_info = {}
    for f in raw_files:
        if f.is_file() and f.name != ".gitkeep":
            h = sha256_file(f)
            sz = f.stat().st_size
            file_info[f.name] = {"sha256": h, "size": sz, "path": str(f)}

    print(f"Total non-gitkeep raw files: {len(file_info)}")
    
    # Check 1037-byte files
    dummy_files = [name for name, info in file_info.items() if info["size"] in (1033, 1037)]
    print(f"Test/Dummy upload files (size ~1037 bytes): {len(dummy_files)}")
    
    real_files = [name for name, info in file_info.items() if info["size"] not in (1033, 1037)]
    print(f"Substantive PDF files (>10KB): {len(real_files)}")
    for name in sorted(real_files):
        info = file_info[name]
        print(f"  {name:50s} size={info['size']:8d} sha256={info['sha256']}")

    with session_scope() as db:
        docs = db.query(SourceDocumentORM).all()
        print(f"\n=== SOURCE DOCUMENTS IN DB ({len(docs)}) ===")
        doc_details = []
        for d in docs:
            clauses = db.query(ClauseORM).filter(ClauseORM.document_id == d.id).all()
            c_count = len(clauses)
            c_embs = sum(1 for c in clauses if c.embedding_verified)
            rules = db.query(RuleORM).join(ClauseORM, RuleORM.clause_id == ClauseORM.clause_id).filter(ClauseORM.document_id == d.id).all()
            r_count = len(rules)
            
            # Check physical file existence and actual hash
            fpath = Path(d.file_path) if d.file_path else None
            actual_hash = None
            actual_size = None
            if fpath and fpath.exists():
                actual_hash = sha256_file(fpath)
                actual_size = fpath.stat().st_size
            elif fpath:
                # Check if file exists under backend/data/raw_sources
                alt_path = raw_dir / fpath.name
                if alt_path.exists():
                    actual_hash = sha256_file(alt_path)
                    actual_size = alt_path.stat().st_size
            
            hash_match = (actual_hash == d.sha256_hash) if actual_hash else False
            is_synth = is_synthetic_document(d)
            
            doc_details.append({
                "id": d.id,
                "title": d.title,
                "authority": d.authority,
                "gazette_no": d.gazette_no,
                "publication_date": str(d.publication_date) if d.publication_date else None,
                "source_url": d.source_url,
                "sha256_hash": d.sha256_hash,
                "file_path": d.file_path,
                "file_size": d.file_size_bytes,
                "actual_size": actual_size,
                "hash_match": hash_match,
                "is_synthetic_flag": d.is_synthetic,
                "is_synthetic_eval": is_synth,
                "clause_count": c_count,
                "verified_embs": c_embs,
                "rule_count": r_count,
            })
            print(f"Doc [{d.id}]:")
            print(f"  Title: {d.title}")
            print(f"  Authority: {d.authority} | Gazette: {d.gazette_no} | PubDate: {d.publication_date}")
            print(f"  URL: {d.source_url}")
            print(f"  DB SHA256: {d.sha256_hash}")
            print(f"  File: {d.file_path} (exists={actual_size is not None}, size={actual_size}, hash_match={hash_match})")
            print(f"  Synthetic: DB={d.is_synthetic}, Evaluated={is_synth}")
            print(f"  Clauses: {c_count} (Verified Embs: {c_embs}) | Rules: {r_count}")

        # Rules audit
        rules = db.query(RuleORM).all()
        print(f"\n=== RULES IN DB ({len(rules)}) ===")
        for r in rules:
            clause = db.query(ClauseORM).filter(ClauseORM.clause_id == r.clause_id, ClauseORM.version_number == r.clause_version).first()
            doc = db.query(SourceDocumentORM).filter(SourceDocumentORM.id == clause.document_id).first() if clause else None
            audit_entries = db.query(HumanReviewAuditORM).filter(HumanReviewAuditORM.rule_id == r.rule_id).all()
            
            quote = (r.source or {}).get("quote_span") if isinstance(r.source, dict) else None
            quote_trunc = (quote[:60] + "...") if quote and len(quote) > 60 else quote
            
            print(f"Rule [{r.rule_id}]:")
            print(f"  Status: {r.review_status} | Gold: {r.is_gold_rule} | Synthetic: DB={r.is_synthetic}, Eval={is_synthetic_rule(r)}")
            print(f"  Outcome: {r.outcome_type}")
            print(f"  Clause: {r.clause_id} (v{r.clause_version}) -> Doc: {clause.document_id if clause else 'ORPHAN'}")
            print(f"  Quote: {quote_trunc}")
            print(f"  Extraction: Model={r.extraction_model}, CrossAgreement={r.cross_agreement}")
            print(f"  Audit Log Entries: {len(audit_entries)}")
            for a in audit_entries:
                print(f"    - [{a.reviewed_at}] {a.reviewer_role} ({a.reviewer_id}): {a.decision} - {a.rationale[:80]}")

        # Clauses audit
        clauses = db.query(ClauseORM).all()
        print(f"\n=== CLAUSES SUMMARY ({len(clauses)}) ===")
        synth_c = sum(1 for c in clauses if is_synthetic_clause(c))
        verif_emb = sum(1 for c in clauses if c.embedding_verified)
        print(f"  Total Clauses: {len(clauses)}")
        print(f"  Synthetic (Evaluated): {synth_c}")
        print(f"  Verified Embeddings: {verif_emb}")
        
        # Check quarantined records
        quarantined_docs = db.query(SourceDocumentORM).filter(SourceDocumentORM.id.like("%test%")).all()
        quarantined_clauses = db.query(ClauseORM).filter(ClauseORM.clause_id.like("%TEST%")).all()
        print(f"  Docs with 'test' in id: {[d.id for d in quarantined_docs]}")
        print(f"  Clauses with 'TEST' in id: {[c.clause_id for c in quarantined_clauses]}")

if __name__ == "__main__":
    main()
