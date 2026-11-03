import sys
import json

sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    RuleORM,
    ClauseORM,
    SourceDocumentORM,
    SYNTHETIC_DOCUMENT_IDS,
    SYNTHETIC_RULE_IDS,
    is_synthetic_document,
    is_synthetic_clause,
    is_synthetic_rule,
)

def reconcile_all_rules():
    with session_scope() as session:
        rules = session.query(RuleORM).order_by(RuleORM.review_status, RuleORM.rule_id).all()
        
        reconciliation = []
        for r in rules:
            clause = session.get(ClauseORM, (r.clause_id, r.clause_version))
            doc = session.get(SourceDocumentORM, clause.document_id) if clause else None
            
            doc_id = doc.id if doc else "UNKNOWN"
            doc_title = doc.title if doc else "UNKNOWN"
            doc_gazette = doc.gazette_no if doc else (r.source.get("gazette_no") if r.source else None)
            
            doc_synthetic = is_synthetic_document(doc, doc_id=doc_id) if doc else False
            clause_synthetic = is_synthetic_clause(clause, clause_id=r.clause_id, document_id=doc_id) if clause else False
            rule_synthetic = is_synthetic_rule(r, rule_id=r.rule_id, clause_id=r.clause_id)
            
            # Execution eligibility:
            # Must be review_status == "APPROVED"
            # In open inquiry without synthetic: must be rule_synthetic == False and clause_synthetic == False and doc_synthetic == False
            is_approved = (r.review_status == "APPROVED")
            eligible_for_execution = is_approved
            
            # Open inquiry visibility for SME
            appears_in_authentic_sme_assessment = is_approved and not rule_synthetic and not doc_synthetic
            
            reconciliation.append({
                "rule_id": r.rule_id,
                "clause_id": r.clause_id,
                "document_id": doc_id,
                "document_title": doc_title,
                "gazette_no": doc_gazette,
                "document_authenticity": "SYNTHETIC" if doc_synthetic else "AUTHENTIC",
                "clause_authenticity": "SYNTHETIC" if clause_synthetic else "AUTHENTIC",
                "rule_authenticity": "SYNTHETIC" if rule_synthetic else "AUTHENTIC",
                "review_status": r.review_status,
                "is_gold_rule": r.is_gold_rule,
                "outcome_type": r.outcome_type,
                "eligible_for_execution": eligible_for_execution,
                "appears_in_authentic_sme_assessment": appears_in_authentic_sme_assessment,
                "notes": (
                    "Authentic Approved Rule" if appears_in_authentic_sme_assessment
                    else ("Authentic Pending Candidate" if not rule_synthetic and not is_approved
                    else "Synthetic Fixture Rule (Isolated at runtime)")
                )
            })
            
        print("RULE_RECONCILIATION_START")
        print(json.dumps(reconciliation, indent=2))
        print("RULE_RECONCILIATION_END")

if __name__ == "__main__":
    reconcile_all_rules()

