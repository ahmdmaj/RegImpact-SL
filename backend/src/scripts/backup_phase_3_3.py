import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    ClauseORM,
    RuleORM,
    HumanReviewAuditORM,
)

def backup_phase_3_3():
    backup_file = Path("backend/data/quarantine/phase3_3_pre_segmentation_backup.json")
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    
    with session_scope() as db:
        docs = db.query(SourceDocumentORM).all()
        clauses = db.query(ClauseORM).all()
        rules = db.query(RuleORM).all()
        audits = db.query(HumanReviewAuditORM).all()
        
        backup_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "source_documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "authority": d.authority,
                    "gazette_no": d.gazette_no,
                    "publication_date": str(d.publication_date) if d.publication_date else None,
                    "source_url": d.source_url,
                    "file_path": d.file_path,
                    "sha256_hash": d.sha256_hash,
                    "is_synthetic": d.is_synthetic,
                }
                for d in docs
            ],
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "version_number": c.version_number,
                    "document_id": c.document_id,
                    "clause_number": c.clause_number,
                    "text": c.text,
                    "start_page": c.start_page,
                    "end_page": c.end_page,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "valid_from": str(c.valid_from) if c.valid_from else None,
                    "valid_to": str(c.valid_to) if c.valid_to else None,
                    "transition_until": str(c.transition_until) if c.transition_until else None,
                    "superseded_by_clause_id": c.superseded_by_clause_id,
                    "is_compilable": c.is_compilable,
                    "embedding_verified": c.embedding_verified,
                    "is_synthetic": c.is_synthetic,
                    "has_embedding": c.embedding is not None,
                }
                for c in clauses
            ],
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "clause_id": r.clause_id,
                    "clause_version": r.clause_version,
                    "outcome_type": r.outcome_type,
                    "review_status": r.review_status,
                    "applies_if": r.applies_if,
                    "exceptions": r.exceptions,
                    "obligation": r.obligation,
                    "validity": r.validity,
                    "source": r.source,
                    "is_gold_rule": getattr(r, "is_gold_rule", False),
                    "is_synthetic": r.is_synthetic,
                }
                for r in rules
            ],
            "audits": [
                {
                    "id": a.id,
                    "rule_id": a.rule_id,
                    "reviewer_id": a.reviewer_id,
                    "reviewer_role": a.reviewer_role,
                    "decision": a.decision,
                    "rationale": a.rationale,
                    "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                }
                for a in audits
            ]
        }
        
        backup_file.write_text(json.dumps(backup_data, indent=2), encoding="utf-8")
        print(f"Backed up {len(docs)} documents, {len(clauses)} clauses, {len(rules)} rules, {len(audits)} audits to {backup_file}")

if __name__ == "__main__":
    backup_phase_3_3()
