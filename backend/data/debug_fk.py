from backend.src.db.models import Base, SourceDocumentORM, ClauseORM, RuleORM
from backend.src.db.session import create_engine_from_url, get_session_factory

engine = create_engine_from_url("sqlite:///:memory:")
Base.metadata.create_all(bind=engine)
session = get_session_factory(engine)()

doc = SourceDocumentORM(
    id="doc1",
    title="title",
    authority="auth",
    file_path="p",
    file_size_bytes=10,
    sha256_hash="h"*64,
    page_count=1,
)
session.add(doc)
session.commit()

clause = ClauseORM(
    clause_id="c1",
    version_number=1,
    document_id="doc1",
    clause_number="1",
    text="txt",
    start_page=1,
    end_page=1,
)
session.add(clause)
session.commit()

rule = RuleORM(
    rule_id="r1",
    clause_id="c1",
    clause_version=1,
    outcome_type="STANDARD",
    applies_if={},
    obligation={},
    validity={},
    source={},
)
session.add(rule)
try:
    session.commit()
    print("SUCCESS INSERTING RULE")
except Exception as e:
    import traceback
    traceback.print_exc()
