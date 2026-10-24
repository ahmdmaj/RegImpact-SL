"""Opt-in live integration test for PostgreSQL with pgvector and native vector distance queries.

Connects to the running PostgreSQL container ONLY if DATABASE_URL is set and reachable.
Cleanly skips if PostgreSQL daemon is unavailable.
"""

from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.src.db.models import Base, ClauseORM, SourceDocumentORM
from backend.src.db.session import create_engine_from_url, create_tables, get_session_factory
from backend.src.engine.retrieval import DenseRetrievalEngine
from backend.src.extraction.embedding_client import MockEmbeddingClient
from backend.tests.conftest import LIVE_DATABASE_URL

DATABASE_URL = (
    LIVE_DATABASE_URL
    if (LIVE_DATABASE_URL and "postgresql" in LIVE_DATABASE_URL.lower())
    else ""
)
IS_POSTGRES = bool(DATABASE_URL and "postgresql" in DATABASE_URL.lower())

def _can_connect_to_postgres() -> bool:
    if not IS_POSTGRES:
        return False
    try:
        engine = create_engine_from_url(DATABASE_URL, connect_args={"connect_timeout": 1})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

POSTGRES_AVAILABLE = _can_connect_to_postgres()


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL daemon is not reachable.")
def test_live_postgres_vector_extension_and_hnsw():
    """Verify that pgvector extension and HNSW index initialize on PostgreSQL."""
    engine = create_engine_from_url(DATABASE_URL)
    create_tables(engine)

    with engine.connect() as conn:
        res = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
        assert res == "vector"

        idx = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname = 'idx_clauses_embedding_hnsw'")
        ).scalar()
        assert idx == "idx_clauses_embedding_hnsw"


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL daemon is not reachable.")
def test_live_postgres_native_vector_search():
    """Verify that DenseRetrievalEngine executes native <=> vector search on PostgreSQL."""
    engine = create_engine_from_url(DATABASE_URL)
    create_tables(engine)
    SessionFactory = get_session_factory(engine)
    session = SessionFactory()

    try:
        # Create a test document
        doc_id = "test_live_doc_pgvector"
        existing_doc = session.query(SourceDocumentORM).filter_by(id=doc_id).first()
        if not existing_doc:
            doc = SourceDocumentORM(
                id=doc_id,
                sha256_hash="deadbeef" * 8,
                title="Live Test Document for Vector Search",
                authority="Test Authority",
                file_path="backend/data/raw_sources/test_live.pdf",
                file_size_bytes=1024,
                page_count=1,
            )
            session.add(doc)
            session.commit()

        # Insert two test clauses with distinct known embeddings
        vec_a = [0.0] * 768
        vec_a[0] = 1.0  # Unit vector along dimension 0

        vec_b = [0.0] * 768
        vec_b[1] = 1.0  # Unit vector along dimension 1

        c1 = ClauseORM(
            clause_id="TEST-VEC-CLAUSE-A",
            version_number=1,
            document_id=doc_id,
            clause_number="Clause A",
            text="Clause A text regarding dairy production capacity",
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=40,
            valid_from="2024-01-01",
            is_compilable=True,
            embedding=vec_a,
        )
        c2 = ClauseORM(
            clause_id="TEST-VEC-CLAUSE-B",
            version_number=1,
            document_id=doc_id,
            clause_number="Clause B",
            text="Clause B text regarding chemical effluent limits",
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=40,
            valid_from="2024-01-01",
            is_compilable=True,
            embedding=vec_b,
        )

        session.merge(c1)
        session.merge(c2)
        session.commit()

        # Query with an embedding client targeting dimension 0
        class MockClientDim0(MockEmbeddingClient):
            def embed_text(self, text: str):
                return vec_a

        retriever = DenseRetrievalEngine(db=session, embedding_client=MockClientDim0())
        results = retriever.search("dairy production", top_k=2)

        assert len(results) >= 2
        # Most similar clause must be Clause A
        assert results[0].clause_id == "TEST-VEC-CLAUSE-A"
        assert results[0].retrieval_method == "dense"
        assert results[0].score > results[1].score

    finally:
        session.rollback()
        session.close()
