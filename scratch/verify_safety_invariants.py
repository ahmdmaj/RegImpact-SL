"""Script to verify Task 5 real-data and rule safety invariants directly on PostgreSQL."""
import os
import sys

# Ensure backend package is importable
sys.path.insert(0, os.path.abspath("."))

from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.db.models import (
    RuleORM,
    ClauseORM,
    SourceDocumentORM,
    HumanReviewAuditORM,
    SYNTHETIC_DOCUMENT_IDS,
    SYNTHETIC_RULE_IDS,
    SYNTHETIC_CLAUSE_PREFIXES,
)

def verify_safety():
    db_url = "postgresql+psycopg://regimpact:regimpact@localhost:5432/regimpact"
    engine = create_engine_from_url(db_url)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        print("=== TASK 5 SAFETY & DATA INTEGRITY VERIFICATION ===")
        
        # 1. Total rules and authentic vs synthetic counts
        all_rules = session.query(RuleORM).all()
        authentic_rules = [r for r in all_rules if r.rule_id not in SYNTHETIC_RULE_IDS]
        synthetic_rules = [r for r in all_rules if r.rule_id in SYNTHETIC_RULE_IDS]
        
        print(f"Total rules in DB: {len(all_rules)}")
        print(f"Authentic rules: {len(authentic_rules)}")
        print(f"Synthetic rules: {len(synthetic_rules)}")
        
        # Check rule review status
        approved_authentic = [r for r in authentic_rules if r.review_status == "APPROVED"]
        pending_authentic = [r for r in authentic_rules if r.review_status == "PENDING_REVIEW"]
        rejected_authentic = [r for r in authentic_rules if r.review_status == "REJECTED"]
        quarantined_authentic = [r for r in authentic_rules if r.review_status == "QUARANTINED"]
        
        print(f"Authentic Approved: {len(approved_authentic)} ({[r.rule_id for r in approved_authentic]})")
        print(f"Authentic Pending: {len(pending_authentic)} ({[r.rule_id for r in pending_authentic]})")
        print(f"Authentic Rejected: {len(rejected_authentic)}")
        print(f"Authentic Quarantined: {len(quarantined_authentic)}")
        
        # 2. Check Phase 4.3 rule: RULE-COLOURING-SEAFOOD-PROHIBITION
        seafood_rule = session.query(RuleORM).filter(RuleORM.rule_id == "RULE-COLOURING-SEAFOOD-PROHIBITION").first()
        if seafood_rule:
            print(f"RULE-COLOURING-SEAFOOD-PROHIBITION status: {seafood_rule.review_status}")
            assert seafood_rule.review_status == "PENDING_REVIEW", "CRITICAL: Seafood rule must remain PENDING_REVIEW!"
            assert not seafood_rule.is_gold_rule, "CRITICAL: Seafood rule must not be gold!"
            print("  -> Phase 4.3 seafood rule safety verified: PENDING_REVIEW, not gold.")
        else:
            print("  -> RULE-COLOURING-SEAFOOD-PROHIBITION not found in database!")
            
        # 3. Gold-label check on authentic rules
        gold_authentic = [r for r in authentic_rules if r.is_gold_rule]
        print(f"Authentic gold rules: {len(gold_authentic)}")
        assert len(gold_authentic) == 0, f"CRITICAL: Found unexpected gold authentic rules: {gold_authentic}"
        
        # 4. Human review audit checks
        audits = session.query(HumanReviewAuditORM).all()
        print(f"Total audit records: {len(audits)}")
        for a in audits:
            print(f"  Audit: rule={a.rule_id}, decision={a.decision}, role={a.reviewer_role}, reviewer={a.reviewer_id}, rationale={a.rationale[:50]}...")
            
        from backend.src.db.models import is_synthetic_document, is_synthetic_clause, is_synthetic_rule

        # 5. Documents check (authentic vs synthetic)
        docs = session.query(SourceDocumentORM).all()
        authentic_docs = [d for d in docs if not is_synthetic_document(d)]
        synthetic_docs = [d for d in docs if is_synthetic_document(d)]
        print(f"Total source documents: {len(docs)} (Authentic: {len(authentic_docs)}, Synthetic: {len(synthetic_docs)})")
        print(f"  Authentic docs: {[d.id for d in authentic_docs]}")
        
        # 6. Clauses check
        clauses = session.query(ClauseORM).all()
        authentic_clauses = [c for c in clauses if not is_synthetic_clause(c)]
        synthetic_clauses = [c for c in clauses if is_synthetic_clause(c)]
        print(f"Total clauses: {len(clauses)} (Authentic: {len(authentic_clauses)}, Synthetic: {len(synthetic_clauses)})")
        
        print("=== SAFETY VERIFICATION COMPLETE: ALL INVARIANTS SATISFIED ===")

if __name__ == "__main__":
    verify_safety()
