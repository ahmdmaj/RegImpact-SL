import sys
sys.stdout.reconfigure(encoding='utf-8')
from backend.tests.conftest import LIVE_DATABASE_URL
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.src.db.models import SourceDocumentORM, DocumentPageORM, ClauseORM, RuleORM, HumanReviewAuditORM

engine = create_engine(LIVE_DATABASE_URL)
with Session(engine) as session:
    docs = session.scalars(select(SourceDocumentORM)).all()
    pages = session.scalars(select(DocumentPageORM)).all()
    clauses = session.scalars(select(ClauseORM)).all()
    rules = session.scalars(select(RuleORM)).all()
    audits = session.scalars(select(HumanReviewAuditORM)).all()

    print(f"=== SOURCE DOCUMENTS ({len(docs)}) ===")
    for d in docs:
        print(f"  ID: {d.id} | SHA256: {d.sha256_hash[:16]}... | Title: {d.title[:45]} | is_synthetic: {d.is_synthetic} | pages: {d.page_count}")

    print(f"\n=== CLAUSES ({len(clauses)}) ===")
    for c in clauses:
        emb_status = "None"
        if c.embedding is not None:
            emb_len = len(c.embedding) if hasattr(c.embedding, '__len__') else 'unknown'
            emb_status = f"dim={emb_len}, verified={c.embedding_verified}, prov={c.embedding_provider}, mod={c.embedding_model}"
        print(f"  ID: {c.clause_id} (v{c.version_number}) | Doc: {c.document_id} | is_synthetic: {c.is_synthetic} | compilable: {c.is_compilable} | Embedding: [{emb_status}]")

    print(f"\n=== RULES ({len(rules)}) ===")
    for r in rules:
        print(f"  ID: {r.rule_id} | Clause: {r.clause_id} | Status: {r.review_status} | Type: {r.outcome_type} | is_synthetic: {getattr(r, 'is_synthetic', False)}")

    print(f"\n=== AUDIT ENTRIES ({len(audits)}) ===")
    for a in audits:
        print(f"  Rule: {a.rule_id} | Reviewer: {a.reviewer_id} ({a.reviewer_role}) | Decision: {a.decision}")
