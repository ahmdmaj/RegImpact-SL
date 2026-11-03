import sys
import json
from pathlib import Path

# Add project root to path
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

def run_corpus_audit():
    with session_scope() as session:
        # 1. Source Documents
        docs = session.query(SourceDocumentORM).all()
        doc_count = len(docs)
        
        doc_summary = []
        for d in docs:
            flag_synthetic = d.is_synthetic
            func_synthetic = is_synthetic_document(d)
            clause_count = session.query(ClauseORM).filter(ClauseORM.document_id == d.id).count()
            page_count = session.query(DocumentPageORM).filter(DocumentPageORM.document_id == d.id).count()
            doc_summary.append({
                "id": d.id,
                "title": d.title,
                "gazette_no": d.gazette_no,
                "authority": d.authority,
                "sha256": d.sha256_hash,
                "page_count_recorded": d.page_count,
                "actual_pages_in_db": page_count,
                "clause_count": clause_count,
                "extraction_status": d.extraction_status,
                "is_synthetic_col": flag_synthetic,
                "is_synthetic_func": func_synthetic,
            })
            
        # 2. Pages
        total_pages = session.query(DocumentPageORM).count()
        doc_2332_pages = session.query(DocumentPageORM).filter(DocumentPageORM.document_id == "doc_2332_03_e").all()
        
        # 3. Clauses
        clauses = session.query(ClauseORM).all()
        total_clauses = len(clauses)
        clauses_with_embedding = session.query(ClauseORM).filter(ClauseORM.embedding.isnot(None)).count()
        clauses_embedding_verified = session.query(ClauseORM).filter(ClauseORM.embedding_verified == True).count()
        
        synthetic_clauses_col = sum(1 for c in clauses if c.is_synthetic)
        synthetic_clauses_func = sum(1 for c in clauses if is_synthetic_clause(c))
        
        doc_2332_clauses = session.query(ClauseORM).filter(ClauseORM.document_id == "doc_2332_03_e").all()
        doc_2332_clauses_with_emb = sum(1 for c in doc_2332_clauses if c.embedding is not None)
        
        # 4. Rules
        rules = session.query(RuleORM).all()
        total_rules = len(rules)
        
        status_counts = {}
        for r in rules:
            status_counts[r.review_status] = status_counts.get(r.review_status, 0) + 1
            
        rules_synthetic_col = sum(1 for r in rules if r.is_synthetic)
        rules_synthetic_func = sum(1 for r in rules if is_synthetic_rule(r))
        
        approved_rules = session.query(RuleORM).filter(RuleORM.review_status == "APPROVED").all()
        pending_rules = session.query(RuleORM).filter(RuleORM.review_status == "PENDING_REVIEW").all()
        rejected_rules = session.query(RuleORM).filter(RuleORM.review_status == "REJECTED").all()
        
        approved_list = []
        for r in approved_rules:
            # find document
            clause = session.get(ClauseORM, (r.clause_id, r.clause_version))
            doc = session.get(SourceDocumentORM, clause.document_id) if clause else None
            approved_list.append({
                "rule_id": r.rule_id,
                "clause_id": r.clause_id,
                "document_id": clause.document_id if clause else "UNKNOWN",
                "gazette_no": doc.gazette_no if doc else (r.source.get("gazette_no") if r.source else None),
                "instrument": doc.title if doc else (r.source.get("instrument") if r.source else None),
                "authority": doc.authority if doc else (r.source.get("authority") if r.source else None),
                "is_synthetic_col": r.is_synthetic,
                "is_synthetic_func": is_synthetic_rule(r),
                "outcome_type": r.outcome_type,
                "applies_if": r.applies_if,
                "obligation_modality": r.obligation.get("modality") if r.obligation else None,
                "obligation_text": r.obligation.get("text") if r.obligation else None,
                "quote_span": r.source.get("quote_span") if r.source else None,
            })
            
        pending_list = []
        for r in pending_rules:
            clause = session.get(ClauseORM, (r.clause_id, r.clause_version))
            doc = session.get(SourceDocumentORM, clause.document_id) if clause else None
            pending_list.append({
                "rule_id": r.rule_id,
                "clause_id": r.clause_id,
                "document_id": clause.document_id if clause else "UNKNOWN",
                "gazette_no": doc.gazette_no if doc else (r.source.get("gazette_no") if r.source else None),
                "instrument": doc.title if doc else (r.source.get("instrument") if r.source else None),
                "is_synthetic_col": r.is_synthetic,
                "is_synthetic_func": is_synthetic_rule(r),
            })
            
        # Rules for doc_2332_03_e
        doc_2332_clause_ids = [c.clause_id for c in doc_2332_clauses]
        doc_2332_rules = [r for r in rules if r.clause_id in doc_2332_clause_ids]
        
        # 5. Review Audits
        audit_records = session.query(HumanReviewAuditORM).all()
        audit_count = len(audit_records)
        
        report = {
            "documents": {
                "total": doc_count,
                "summary": doc_summary,
            },
            "pages": {
                "total": total_pages,
                "doc_2332_pages_count": len(doc_2332_pages),
                "doc_2332_page_numbers": sorted([p.page_number for p in doc_2332_pages]),
            },
            "clauses": {
                "total": total_clauses,
                "with_embedding": clauses_with_embedding,
                "embedding_verified": clauses_embedding_verified,
                "synthetic_col_count": synthetic_clauses_col,
                "synthetic_func_count": synthetic_clauses_func,
                "doc_2332_clause_count": len(doc_2332_clauses),
                "doc_2332_clauses_with_embedding": doc_2332_clauses_with_emb,
            },
            "rules": {
                "total": total_rules,
                "status_breakdown": status_counts,
                "synthetic_col_count": rules_synthetic_col,
                "synthetic_func_count": rules_synthetic_func,
                "doc_2332_rules_count": len(doc_2332_rules),
                "approved_rules": approved_list,
                "pending_rules": pending_list,
                "rejected_count": len(rejected_rules),
            },
            "review_audits": {
                "total": audit_count,
                "records": [
                    {
                        "rule_id": a.rule_id,
                        "action": a.action,
                        "reviewer_id": a.reviewer_id,
                        "rationale": a.rationale,
                        "timestamp": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in audit_records
                ]
            }
        }
        
        with open("scratch/corpus_audit_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            
        print("Corpus audit completed successfully! Written to scratch/corpus_audit_report.json")
        print(f"Total documents: {doc_count}")
        print(f"Total pages: {total_pages}")
        print(f"Total clauses: {total_clauses} (with embeddings: {clauses_with_embedding})")
        print(f"Total rules: {total_rules} (Approved: {len(approved_rules)}, Pending: {len(pending_rules)}, Rejected: {len(rejected_rules)})")
        print(f"doc_2332_03_e: pages={len(doc_2332_pages)}, clauses={len(doc_2332_clauses)}, embeddings={doc_2332_clauses_with_emb}, rules={len(doc_2332_rules)}")

if __name__ == "__main__":
    run_corpus_audit()
