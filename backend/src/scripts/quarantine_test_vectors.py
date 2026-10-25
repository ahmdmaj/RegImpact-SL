"""Script to safely backup and reversibly quarantine test-vector records in PostgreSQL.

Change Plan:
1. Export current state of test_live_doc_pgvector, TEST-VEC-CLAUSE-A, TEST-VEC-CLAUSE-B to backend/data/quarantine/test_vector_records_backup.json.
2. Update records in PostgreSQL:
   - SourceDocumentORM(id='test_live_doc_pgvector'): set is_synthetic = True.
   - ClauseORM(clause_id='TEST-VEC-CLAUSE-A'): set is_synthetic = True, embedding_verified = False.
   - ClauseORM(clause_id='TEST-VEC-CLAUSE-B'): set is_synthetic = True, embedding_verified = False.
3. Commit transaction. Zero records deleted, truncated, or dropped.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, SourceDocumentORM
from backend.tests.conftest import LIVE_DATABASE_URL

def execute_quarantine() -> None:
    if not LIVE_DATABASE_URL or "postgresql" not in LIVE_DATABASE_URL.lower():
        print("Live PostgreSQL not available; skipping live database quarantine.")
        return

    engine = create_engine(LIVE_DATABASE_URL)
    with Session(engine) as session:
        doc = session.get(SourceDocumentORM, "test_live_doc_pgvector")
        c1 = session.get(ClauseORM, ("TEST-VEC-CLAUSE-A", 1))
        c2 = session.get(ClauseORM, ("TEST-VEC-CLAUSE-B", 1))

        if not doc and not c1 and not c2:
            print("No contaminated test records found in live database.")
            return

        # 1. Export backup
        quarantine_dir = Path("backend/data/quarantine")
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        backup_file = quarantine_dir / "test_vector_records_backup.json"

        backup_data = {
            "source_document": {
                "id": doc.id if doc else None,
                "title": doc.title if doc else None,
                "sha256_hash": doc.sha256_hash if doc else None,
                "is_synthetic": doc.is_synthetic if doc else None,
            } if doc else None,
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "version_number": c.version_number,
                    "document_id": c.document_id,
                    "is_synthetic": c.is_synthetic,
                    "embedding_verified": c.embedding_verified,
                    "embedding_provider": c.embedding_provider,
                    "embedding_model": c.embedding_model,
                    "vector_head": c.embedding[:5] if c.embedding else None,
                }
                for c in [c1, c2] if c is not None
            ]
        }
        backup_file.write_text(json.dumps(backup_data, indent=2), encoding="utf-8")
        print(f"Exported backup to {backup_file}")

        # 2. Reversible quarantine: mark is_synthetic=True and embedding_verified=False
        if doc:
            doc.is_synthetic = True
            print("Quarantined SourceDocumentORM(id='test_live_doc_pgvector') -> is_synthetic=True")
        if c1:
            c1.is_synthetic = True
            c1.embedding_verified = False
            print("Quarantined ClauseORM(id='TEST-VEC-CLAUSE-A') -> is_synthetic=True, embedding_verified=False")
        if c2:
            c2.is_synthetic = True
            c2.embedding_verified = False
            print("Quarantined ClauseORM(id='TEST-VEC-CLAUSE-B') -> is_synthetic=True, embedding_verified=False")

        session.commit()
        print("Reversible quarantine committed successfully. 0 records deleted.")

if __name__ == "__main__":
    execute_quarantine()
