"""Milestone 3 unit tests: Lexical (BM25), Dense vector, and Hybrid RRF retrieval.

All tests run completely offline against SQLite in-memory DB and MockEmbeddingClient.
Test coverage:
  RET-BM25-001  BM25 finds clauses matching statutory keywords.
  RET-BM25-002  BM25 ranks clauses with higher query term relevance higher.
  RET-BM25-003  BM25 filtering by document_id and is_compilable works.
  RET-BM25-004  BM25 handles empty query and empty corpus gracefully.
  RET-DENSE-001 Dense retrieval indexes clauses and performs vector similarity search.
  RET-DENSE-002 Dense retrieval ranks semantically overlapping clauses higher.
  RET-DENSE-003 Dense retrieval filters by document_id.
  RET-DENSE-004 index_clauses populates embeddings for unindexed clauses.
  RET-HYBRID-001 Hybrid RRF combines BM25 and Dense ranks using formula 1 / (60 + rank).
  RET-HYBRID-002 Clauses appearing in both BM25 and Dense top ranks receive higher RRF scores.
  RET-GAP-001   Clause lacking any rule is flagged coverage_gap=True.
  RET-GAP-002   Clause with PENDING_REVIEW rule is flagged coverage_gap=True.
  RET-GAP-003   Clause with APPROVED rule is flagged has_approved_rule=True, coverage_gap=False.
  RET-EMB-001   MockEmbeddingClient produces unit-normalized vectors of expected dimension.
  RET-EMB-002   MockEmbeddingClient yields higher similarity for shared legal terminology.
  RET-EMB-003   get_embedding_client falls back to MockEmbeddingClient safely without credentials.
"""

from __future__ import annotations

import math
from typing import List
import pytest
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    RetrievalResult,
    cross_reference_coverage_gaps,
)
from backend.src.extraction.embedding_client import (
    MockEmbeddingClient,
    get_embedding_client,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def populated_db(db_session: Session) -> Session:
    """Populate database with 4 distinct regulatory clauses across 2 source documents."""
    # Source Document 1: Food Act Regulations
    doc1 = SourceDocumentORM(
        id="doc_food_act_2024",
        sha256_hash="1111111111111111111111111111111111111111111111111111111111111111",
        title="Food (Labelling and Advertising) Regulations 2024",
        authority="Food Control Administration Unit",
        file_path="backend/data/raw_sources/food_act.pdf",
        file_size_bytes=5000,
        page_count=10,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    # Source Document 2: Environmental Protection Act
    doc2 = SourceDocumentORM(
        id="doc_nea_epl_2024",
        sha256_hash="2222222222222222222222222222222222222222222222222222222222222222",
        title="National Environmental Protection Regulations 2024",
        authority="Central Environmental Authority",
        file_path="backend/data/raw_sources/cea_epl.pdf",
        file_size_bytes=8000,
        page_count=15,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add_all([doc1, doc2])
    db_session.flush()

    # Clause 1: Food labelling threshold
    c1 = ClauseORM(
        clause_id="CLAUSE-FOOD-004",
        version_number=1,
        document_id="doc_food_act_2024",
        clause_number="Regulation 4",
        text=(
            "Regulation 4. Every food manufacturing enterprise having a production capacity "
            "of 50 kg per day or more shall ensure that each retail package carries a nutrition information panel."
        ),
        start_page=1,
        end_page=1,
        char_start=0,
        char_end=170,
        is_compilable=True,
    )
    # Clause 2: Food allergen warning
    c2 = ClauseORM(
        clause_id="CLAUSE-FOOD-005",
        version_number=1,
        document_id="doc_food_act_2024",
        clause_number="Regulation 5",
        text=(
            "Regulation 5. Where any prepackaged food product contains allergens including peanuts, gluten, "
            "or milk derivatives, an explicit allergen statement shall be displayed prominently on the container."
        ),
        start_page=2,
        end_page=2,
        char_start=0,
        char_end=190,
        is_compilable=True,
    )
    # Clause 3: Environmental Protection Licence (EPL)
    c3 = ClauseORM(
        clause_id="CLAUSE-EPL-012",
        version_number=1,
        document_id="doc_nea_epl_2024",
        clause_number="Schedule 1 Part B Item 12",
        text=(
            "Schedule 1 Part B Item 12. Any industrial manufacturing activity discharging industrial effluents "
            "or employing 20 or more persons shall obtain an Environmental Protection Licence (EPL) prior to operation."
        ),
        start_page=3,
        end_page=3,
        char_start=0,
        char_end=200,
        is_compilable=True,
    )
    # Clause 4: Non-compilable / Discretionary clause
    c4 = ClauseORM(
        clause_id="CLAUSE-EPL-099",
        version_number=1,
        document_id="doc_nea_epl_2024",
        clause_number="Section 99",
        text=(
            "Section 99. The Minister may in his sole discretion waive any requirement under these regulations "
            "where he deems it expedient in the public interest."
        ),
        start_page=10,
        end_page=10,
        char_start=0,
        char_end=150,
        is_compilable=False,
        non_compilable_reason="Ministerial discretion cannot be resolved deterministically.",
    )
    db_session.add_all([c1, c2, c3, c4])
    db_session.flush()

    # Add Rule for Clause 1 (APPROVED)
    r1 = RuleORM(
        rule_id="RULE-FOOD-004",
        clause_id="CLAUSE-FOOD-004",
        clause_version=1,
        outcome_type="STANDARD",
        applies_if={"all": [{"field": "production_capacity.kg_per_day", "op": "gte", "value": 50}]},
        exceptions=[],
        obligation={"type": "labelling", "text": "Display nutrition panel", "impact_categories": ["labelling"]},
        validity={"published": "2024-01-01", "commences": "2024-06-01"},
        source={"clause": "Regulation 4", "instrument": "Food Act", "quote_span": "50 kg per day"},
        review_status="APPROVED",
    )
    # Add Rule for Clause 2 (PENDING_REVIEW)
    r2 = RuleORM(
        rule_id="RULE-FOOD-005",
        clause_id="CLAUSE-FOOD-005",
        clause_version=1,
        outcome_type="STANDARD",
        applies_if={"all": [{"field": "allergens", "op": "contains", "value": "peanuts"}]},
        exceptions=[],
        obligation={"type": "labelling", "text": "Display allergen statement", "impact_categories": ["labelling"]},
        validity={"published": "2024-01-01", "commences": "2024-06-01"},
        source={"clause": "Regulation 5", "instrument": "Food Act", "quote_span": "allergens"},
        review_status="PENDING_REVIEW",
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    return db_session


# ---------------------------------------------------------------------------
# BM25 Lexical Tests
# ---------------------------------------------------------------------------

def test_ret_bm25_001_exact_match(populated_db):
    """BM25 finds clause matching specific keyword."""
    engine = BM25RetrievalEngine(populated_db)
    results = engine.search("nutrition information panel", top_k=2)

    assert len(results) > 0
    top = results[0]
    assert top.clause_id == "CLAUSE-FOOD-004"
    assert top.retrieval_method == "bm25"
    assert top.rank == 1
    assert "nutrition information panel" in top.text.lower()


def test_ret_bm25_002_relative_ranking(populated_db):
    """BM25 ranks environmental clause top for effluent query."""
    engine = BM25RetrievalEngine(populated_db)
    results = engine.search("industrial effluents Environmental Protection Licence", top_k=3)

    assert len(results) > 0
    assert results[0].clause_id == "CLAUSE-EPL-012"
    assert results[0].score > 0.0


def test_ret_bm25_003_metadata_filters(populated_db):
    """BM25 strictly filters by document_id and compilability."""
    engine = BM25RetrievalEngine(populated_db)

    # Filter by Food Act document
    results_food = engine.search(
        "regulations", top_k=10, filters={"document_id": "doc_food_act_2024"}
    )
    for r in results_food:
        assert r.document_id == "doc_food_act_2024"

    # Filter out non-compilable clauses
    results_compilable = engine.search(
        "regulations public interest", top_k=10, filters={"is_compilable": True}
    )
    clause_ids = [r.clause_id for r in results_compilable]
    assert "CLAUSE-EPL-099" not in clause_ids


def test_ret_bm25_004_empty_query(populated_db):
    """BM25 returns empty list on blank or stopword query."""
    engine = BM25RetrievalEngine(populated_db)
    assert engine.search("") == []
    assert engine.search("   ") == []


# ---------------------------------------------------------------------------
# Dense Vector Tests
# ---------------------------------------------------------------------------

def test_ret_dense_001_index_and_search(populated_db):
    """Dense retriever indexes clauses and executes vector search."""
    emb_client = MockEmbeddingClient(dimension=128)
    engine = DenseRetrievalEngine(populated_db, embedding_client=emb_client)

    # 1. Index all clauses
    indexed_count = engine.index_clauses()
    assert indexed_count == 4

    # 2. Search for food allergens
    results = engine.search("prepackaged food product allergen warning", top_k=2)
    assert len(results) > 0
    assert results[0].retrieval_method == "dense"
    assert results[0].clause_id == "CLAUSE-FOOD-005"
    assert results[0].score > 0.0


def test_ret_dense_002_semantic_ranking(populated_db):
    """Dense retriever ranks environmental clause highest for environmental query."""
    emb_client = MockEmbeddingClient(dimension=128)
    engine = DenseRetrievalEngine(populated_db, embedding_client=emb_client)
    engine.index_clauses()

    results = engine.search("industrial manufacturing licence effluent", top_k=2)
    assert len(results) > 0
    assert results[0].clause_id == "CLAUSE-EPL-012"


def test_ret_dense_003_filter_by_document(populated_db):
    """Dense retriever obeys document_id filter."""
    emb_client = MockEmbeddingClient(dimension=128)
    engine = DenseRetrievalEngine(populated_db, embedding_client=emb_client)
    engine.index_clauses()

    results = engine.search(
        "enterprise requirements", top_k=5, filters={"document_id": "doc_nea_epl_2024"}
    )
    for r in results:
        assert r.document_id == "doc_nea_epl_2024"


def test_ret_dense_004_idempotent_indexing(populated_db):
    """index_clauses does not re-compute embeddings when already stored."""
    emb_client = MockEmbeddingClient(dimension=128)
    engine = DenseRetrievalEngine(populated_db, embedding_client=emb_client)

    count1 = engine.index_clauses()
    assert count1 == 4

    # Calling again should index 0
    count2 = engine.index_clauses()
    assert count2 == 0


# ---------------------------------------------------------------------------
# Hybrid RRF Tests
# ---------------------------------------------------------------------------

def test_ret_hybrid_001_rrf_scoring(populated_db):
    """Hybrid ranker calculates RRF score combining BM25 and Dense ranks."""
    emb_client = MockEmbeddingClient(dimension=128)
    dense_eng = DenseRetrievalEngine(populated_db, embedding_client=emb_client)
    dense_eng.index_clauses()

    bm25_eng = BM25RetrievalEngine(populated_db)
    hybrid_eng = HybridRetrievalEngine(
        populated_db, bm25_engine=bm25_eng, dense_engine=dense_eng, rrf_k=60
    )

    results = hybrid_eng.search("food manufacturing production capacity 50 kg", top_k=2)

    assert len(results) > 0
    top = results[0]
    assert top.clause_id == "CLAUSE-FOOD-004"
    assert top.retrieval_method == "hybrid_rrf"
    assert top.rank == 1

    # Theoretical maximum RRF for rank 1 in both engines is 1/(60+1) + 1/(60+1) ~= 0.03279
    expected_max = 2.0 / 61.0
    assert top.score <= round(expected_max, 5) + 0.001
    assert top.score > 0.01


def test_ret_hybrid_002_promotes_consensus_passages(populated_db):
    """A passage returned in the top rank by both BM25 and Dense gets top RRF score."""
    emb_client = MockEmbeddingClient(dimension=128)
    dense_eng = DenseRetrievalEngine(populated_db, embedding_client=emb_client)
    dense_eng.index_clauses()

    bm25_eng = BM25RetrievalEngine(populated_db)
    hybrid_eng = HybridRetrievalEngine(
        populated_db, bm25_engine=bm25_eng, dense_engine=dense_eng
    )

    results = hybrid_eng.search("environmental protection licence industrial effluents", top_k=4)
    assert results[0].clause_id == "CLAUSE-EPL-012"


# ---------------------------------------------------------------------------
# Coverage Gap Tests
# ---------------------------------------------------------------------------

def test_ret_gap_001_uncompiled_clause_is_coverage_gap(populated_db):
    """Clause lacking any rule has has_approved_rule=False and coverage_gap=True."""
    engine = BM25RetrievalEngine(populated_db)
    results = engine.search("discretion public interest", top_k=5)

    res_99 = next((r for r in results if r.clause_id == "CLAUSE-EPL-099"), None)
    assert res_99 is not None
    assert res_99.has_approved_rule is False
    assert res_99.coverage_gap is True


def test_ret_gap_002_pending_review_rule_is_coverage_gap(populated_db):
    """Clause whose rule is PENDING_REVIEW is still flagged as coverage gap."""
    engine = BM25RetrievalEngine(populated_db)
    results = engine.search("allergens peanuts gluten", top_k=5)

    res_5 = next((r for r in results if r.clause_id == "CLAUSE-FOOD-005"), None)
    assert res_5 is not None
    assert res_5.has_approved_rule is False
    assert res_5.coverage_gap is True


def test_ret_gap_003_approved_rule_has_no_gap(populated_db):
    """Clause whose rule is APPROVED has has_approved_rule=True and coverage_gap=False."""
    engine = BM25RetrievalEngine(populated_db)
    results = engine.search("nutrition information panel 50 kg", top_k=5)

    res_4 = next((r for r in results if r.clause_id == "CLAUSE-FOOD-004"), None)
    assert res_4 is not None
    assert res_4.has_approved_rule is True
    assert res_4.coverage_gap is False


# ---------------------------------------------------------------------------
# MockEmbeddingClient Tests
# ---------------------------------------------------------------------------

def test_ret_emb_001_mock_client_dimension_and_norm():
    """MockEmbeddingClient produces unit-normalized vectors."""
    client = MockEmbeddingClient(dimension=64)
    vec = client.embed_text("sample legal text")

    assert len(vec) == 64
    # Check L2 norm is ~ 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4


def test_ret_emb_002_mock_client_semantic_overlap():
    """Texts sharing words have higher dot product than unrelated texts."""
    client = MockEmbeddingClient(dimension=128)

    v1 = client.embed_text("food manufacturing enterprise production capacity")
    v2 = client.embed_text("food manufacturing capacity limits")
    v3 = client.embed_text("hazardous chemical radioactive waste disposal")

    sim_related = sum(a * b for a, b in zip(v1, v2))
    sim_unrelated = sum(a * b for a, b in zip(v1, v3))

    assert sim_related > sim_unrelated


def test_ret_emb_003_factory_mock_fallback(monkeypatch):
    """get_embedding_client returns MockEmbeddingClient when keys are unset."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    client = get_embedding_client(allow_mock_fallback=True)
    assert isinstance(client, MockEmbeddingClient)


def test_ret_dense_native_pgvector_dispatch(monkeypatch, populated_db):
    """DenseRetrievalEngine dispatches to native pgvector on postgres dialect and fallback on sqlite."""
    engine = DenseRetrievalEngine(db=populated_db)
    engine.index_clauses()

    # On SQLite, verifies in-memory fallback runs successfully
    results_sqlite = engine.search("prepackaged labelling", top_k=2)
    assert len(results_sqlite) > 0
    assert results_sqlite[0].retrieval_method == "dense"

    # Verify that if dialect is postgresql, _search_native_pgvector is invoked
    called = []
    def fake_native(query_vec, top_k=10, filters=None):
        called.append(True)
        return results_sqlite

    monkeypatch.setattr(engine, "_search_native_pgvector", fake_native)
    class FakeDialect:
        name = "postgresql"
    class FakeBind:
        dialect = FakeDialect()

    monkeypatch.setattr(populated_db, "get_bind", lambda: FakeBind())
    res = engine.search("prepackaged labelling", top_k=2)
    assert len(called) == 1
    assert res == results_sqlite
