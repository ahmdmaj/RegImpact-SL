import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.db.session import session_scope

QUARANTINE_DOC_IDS = [
    # 6 integration test dummy uploads (size ~1037 bytes)
    "doc_291759ecef9fc7c9129bff1139d1837790a50cac32236ec46c0e4b351d76270c",
    "doc_3e863d976d56eb45ca7d410173fd8b451d6fef7308cceb706afe6720cec78b7f",
    "doc_3f75e3ac63af8670c6ddda34fa8a61d2869e7697d5c88dfaee34162f5036f6e1",
    "doc_58a58c41bf7d133299fd0fc96a8057f321d0ebfc8d0292fb72ae9c77bc2be3d7",
    "doc_6530c833247216f50bf6761120432ef8395c53f2ac68966efbe177774b6828e0",
    "doc_c244fce78aa38cfc17dbd9029caf602d50bd10bfdfd6fcb20bc215e0b8d47bb8",
    # Non-statutory lecture slides
    "doc_lec_03",
    # Unpromulgated draft
    "doc_labelling_regulations_final_2026",
    # Synthetic fixtures with pseudo-hashes
    "doc_fcau_labelling_2024",
    "doc_cea_epl_2022",
    "doc_caa_mrp_2023",
]

QUARANTINE_RULE_IDS = [
    "RULE-FCAU-REG-4",
    "RULE-FCAU-REG-15",
    "RULE-CEA-REG-3",
    "RULE-CEA-REG-8",
    "RULE-CAA-SEC-10",
    "RULE-CAA-SEC-14",
    "RULE-FCAU-001",
    "RULE-CEA-EPL-001",
    "RULE-FCAU-REAL-2026-REG-2",  # Grounded in unpromulgated draft
]


def execute_remediation(dry_run: bool = False):
    backup_path = Path("backend/data/quarantine/phase3_1_remediation_backup.json")
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    with session_scope() as db:
        # 1. Collect records for backup
        backup_data = {
            "source_documents": [],
            "clauses": [],
            "rules": [],
        }

        docs = db.query(SourceDocumentORM).filter(SourceDocumentORM.id.in_(QUARANTINE_DOC_IDS)).all()
        for d in docs:
            backup_data["source_documents"].append({
                "id": d.id,
                "title": d.title,
                "is_synthetic": d.is_synthetic,
                "sha256_hash": d.sha256_hash,
                "file_path": d.file_path,
            })

        clauses = db.query(ClauseORM).filter(ClauseORM.document_id.in_(QUARANTINE_DOC_IDS)).all()
        for c in clauses:
            backup_data["clauses"].append({
                "clause_id": c.clause_id,
                "document_id": c.document_id,
                "is_synthetic": c.is_synthetic,
                "embedding_verified": c.embedding_verified,
                "embedding_provider": c.embedding_provider,
                "embedding_model": c.embedding_model,
            })

        rules = db.query(RuleORM).filter(RuleORM.rule_id.in_(QUARANTINE_RULE_IDS)).all()
        for r in rules:
            backup_data["rules"].append({
                "rule_id": r.rule_id,
                "clause_id": r.clause_id,
                "review_status": r.review_status,
                "is_synthetic": r.is_synthetic,
            })

        backup_path.write_text(json.dumps(backup_data, indent=2), encoding="utf-8")
        print(f"Exported backup of {len(docs)} docs, {len(clauses)} clauses, {len(rules)} rules to {backup_path}")

        if dry_run:
            print("DRY RUN: No database modifications applied.")
            return

        # 2. Apply reversible quarantine to source documents
        for d in docs:
            d.is_synthetic = True
            print(f"Quarantined Doc: {d.id} -> is_synthetic=True")

        # 3. Apply reversible quarantine to clauses
        for c in clauses:
            c.is_synthetic = True
            # For test dummy uploads and draft doc, invalidate embedding_verified flag
            if c.document_id in (
                "doc_291759ecef9fc7c9129bff1139d1837790a50cac32236ec46c0e4b351d76270c",
                "doc_3e863d976d56eb45ca7d410173fd8b451d6fef7308cceb706afe6720cec78b7f",
                "doc_3f75e3ac63af8670c6ddda34fa8a61d2869e7697d5c88dfaee34162f5036f6e1",
                "doc_58a58c41bf7d133299fd0fc96a8057f321d0ebfc8d0292fb72ae9c77bc2be3d7",
                "doc_6530c833247216f50bf6761120432ef8395c53f2ac68966efbe177774b6828e0",
                "doc_c244fce78aa38cfc17dbd9029caf602d50bd10bfdfd6fcb20bc215e0b8d47bb8",
                "doc_labelling_regulations_final_2026",
            ):
                c.embedding_verified = False
            print(f"Quarantined Clause: {c.clause_id} -> is_synthetic=True, emb_verified={c.embedding_verified}")

        # 4. Apply reversible quarantine to rules
        for r in rules:
            r.is_synthetic = True
            print(f"Quarantined Rule: {r.rule_id} -> is_synthetic=True (status remains {r.review_status})")

        db.flush()
        print("\nDatabase transaction successfully flushed and committed.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    execute_remediation(dry_run=dry)
