"""Phase 4.5 Regression Test Suite: RAG Runtime Integration and Retrieval Verification.

Verifies:
1. Runtime selection of intended embedding client (SentenceTransformerEmbeddingClient / BAAI/bge-base-en-v1.5).
2. Compatibility between query embedding configuration and stored 768-d vector dimensions.
3. Clear failure behavior when configured embedding model cannot load.
4. Useful query tokenization for snake_case values (e.g. food_manufacturing -> food manufacturing).
5. Inclusion of product names, categories, and packaging attributes in retrieval query.
6. Safe handling of missing optional profile fields.
7. Dense retrieval execution against supported test double and native environments.
8. Hybrid retrieval behavior (hybrid_rrf) when dense and BM25 retrieval succeed.
9. Explicit, intentional BM25-only retrieval mode (bm25_only).
10. Preservation of source and clause provenance across retrieval results.
"""

from __future__ import annotations

import math
import os
from typing import Any, List
import pytest
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, SourceDocumentORM
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    RetrievalResult,
    _tokenize,
    build_retrieval_query,
    normalize_query_text,
)
from backend.src.extraction.embedding_client import (
    BaseEmbeddingClient,
    MockEmbeddingClient,
    SentenceTransformerEmbeddingClient,
    get_embedding_client,
)
from backend.src.extraction.llm_client import LLMClientError
from backend.src.models.domain import BusinessProfile, Market, Product


# ---------------------------------------------------------------------------
# 1. Runtime Selection and Dimension Compatibility
# ---------------------------------------------------------------------------

def test_runtime_selection_of_intended_embedding_client(monkeypatch):
    """Verify runtime factory instantiates SentenceTransformerEmbeddingClient for BGE model."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "sentence-transformers")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "768")

    client = get_embedding_client(allow_mock_fallback=False)
    assert isinstance(client, SentenceTransformerEmbeddingClient)
    assert client.provider_name == "sentence-transformers"
    assert client.model_name == "BAAI/bge-base-en-v1.5"
    assert client.dimension == 768
    assert client.is_verified is True

    provenance = client.get_provenance()
    assert provenance["provider"] == "sentence-transformers"
    assert provenance["model"] == "BAAI/bge-base-en-v1.5"
    assert provenance["dimension"] == 768
    assert provenance["is_verified"] is True


def test_query_embedding_compatibility_with_stored_dimension():
    """Verify query embedding produces exactly 768-d unit-normalized vectors matching stored schema."""
    client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5", dimension=768)
    query = "colouring substances fish molluscs crustaceans echinoderms"
    q_vec = client.embed_query(query)

    assert len(q_vec) == 768
    assert all(math.isfinite(x) for x in q_vec)
    norm = math.sqrt(sum(x * x for x in q_vec))
    assert abs(norm - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# 2. Clear Failure Behavior
# ---------------------------------------------------------------------------

def test_clear_failure_when_configured_model_cannot_load(monkeypatch, db_session: Session):
    """When configured model fails to load, Dense engine must fail clearly with LLMClientError."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "sentence-transformers")
    monkeypatch.setenv("EMBEDDING_MODEL", "non-existent-org/invalid-model-name-xyz-999")

    # DenseRetrievalEngine initializes and records init_error
    dense_engine = DenseRetrievalEngine(db=db_session)
    assert dense_engine.init_error is not None

    # search() must raise LLMClientError instead of silently returning []
    with pytest.raises(LLMClientError) as exc_info:
        dense_engine.search("food colouring")

    assert "configured embedding model failed to load" in str(exc_info.value).lower()


def test_clear_failure_during_query_embedding_propagates(monkeypatch, db_session: Session):
    """When query embedding raises an error at search time, LLMClientError is raised."""
    failing_client = MockEmbeddingClient(dimension=768)
    def fail_embed(text: str):
        raise RuntimeError("Inference engine disconnected")
    failing_client.embed_query = fail_embed  # type: ignore

    dense_engine = DenseRetrievalEngine(db=db_session, embedding_client=failing_client, allow_unverified=True)

    with pytest.raises(LLMClientError) as exc_info:
        dense_engine.search("sample query")

    assert "query embedding" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 3. Query Construction and Snake_case Tokenization
# ---------------------------------------------------------------------------

def test_snake_case_query_tokenization():
    """Verify snake_case and kebab-case tokens are separated into clean natural-language terms."""
    # Test BM25 tokenizer
    tokens = _tokenize("food_manufacturing and dairy_products-processing")
    assert "food" in tokens
    assert "manufacturing" in tokens
    assert "dairy" in tokens
    assert "products" in tokens
    assert "processing" in tokens
    assert "food_manufacturing" not in tokens

    # Test query normalizer
    norm_tokens = normalize_query_text("seafood_processing/fish_molluscs")
    assert norm_tokens == ["seafood", "processing", "fish", "molluscs"]


def test_query_construction_includes_products_and_categories():
    """Verify build_retrieval_query incorporates activity, industry, product names, and categories."""
    profile = BusinessProfile(
        business_id="BIZ-TEST-001",
        activity="food_manufacturing",
        industry="food_and_beverage",
        products=[
            Product(name="Frozen Raw Prawns", category="fish", prepackaged=True),
            Product(name="Bottled Mixed Fruit Jam", category="jams_jellies_marmalades", prepackaged=True),
        ],
        market=Market(b2b_only=True),
    )

    query = build_retrieval_query(profile)

    # Activity & industry
    assert "food" in query
    assert "manufacturing" in query
    assert "beverage" in query
    # Products
    assert "frozen" in query
    assert "prawns" in query
    assert "fish" in query
    assert "jam" in query
    assert "jams" in query
    assert "jellies" in query
    assert "marmalades" in query
    # Flags
    assert "prepackaged" in query
    assert "b2b" in query


def test_query_construction_handles_missing_optional_fields_safely():
    """Verify missing fields gracefully fall back without throwing or inventing terms."""
    # None profile
    assert build_retrieval_query(None) == "food manufacturing"

    # Empty profile
    empty_profile = BusinessProfile()
    assert build_retrieval_query(empty_profile) == "food manufacturing"

    # Profile with only activity
    act_profile = BusinessProfile(activity="catering_services")
    assert build_retrieval_query(act_profile) == "catering services"

    # Profile with dictionary format
    dict_profile = {
        "activity": "tea_packaging",
        "products": [{"category": "bulk_tea", "prepackaged": False}],
    }
    assert build_retrieval_query(dict_profile) == "tea packaging bulk"


# ---------------------------------------------------------------------------
# 4. Dense and Hybrid Retrieval Behavior
# ---------------------------------------------------------------------------

def test_hybrid_retrieval_combines_dense_and_bm25_when_dense_succeeds(db_session: Session):
    """Verify HybridRetrievalEngine reports hybrid_rrf when both BM25 and Dense return candidates."""
    doc = SourceDocumentORM(
        id="doc_hybrid_success_test",
        title="Food Standards Gazette",
        authority="FCAU",
        sha256_hash="a" * 64,
        file_path="dummy.pdf",
        file_size_bytes=1000,
        page_count=1,
        extraction_status="SUCCESS",
    )
    # Clause 1
    c1 = ClauseORM(
        clause_id="CLAUSE-SEAFOOD-PROHIBITION-01",
        version_number=1,
        document_id="doc_hybrid_success_test",
        clause_number="Reg 5(iv)",
        text="No person shall use any colouring substance in or upon any fish, molluscs, crustaceans or echinoderms.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    # Clause 2
    c2 = ClauseORM(
        clause_id="CLAUSE-GENERAL-LABELLING-01",
        version_number=1,
        document_id="doc_hybrid_success_test",
        clause_number="Reg 3",
        text="All prepackaged food products sold at retail must be labelled in English, Sinhala and Tamil.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    db_session.add_all([doc, c1, c2])
    db_session.flush()

    emb_client = MockEmbeddingClient(dimension=768)
    dense_engine = DenseRetrievalEngine(db=db_session, embedding_client=emb_client, allow_unverified=True)
    dense_engine.index_clauses()

    hybrid_engine = HybridRetrievalEngine(db=db_session, dense_engine=dense_engine, allow_unverified=True)
    results = hybrid_engine.search("colouring substance fish molluscs crustaceans", top_k=5)

    assert len(results) > 0
    top = results[0]
    assert top.clause_id == "CLAUSE-SEAFOOD-PROHIBITION-01"
    assert top.retrieval_method == "hybrid_rrf"
    assert top.metadata.get("dense_active") is True
    assert top.metadata.get("bm25_active") is True
    assert top.metadata.get("fallback_reason") is None


def test_intentional_bm25_only_mode(monkeypatch, db_session: Session):
    """When EMBEDDING_PROVIDER is 'bm25' or 'none', retrieval executes purely in bm25_only mode."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bm25")

    doc = SourceDocumentORM(
        id="doc_bm25_only_test",
        title="Labelling Regulation Document",
        authority="FCAU",
        sha256_hash="b" * 64,
        file_path="dummy.pdf",
        file_size_bytes=1000,
        page_count=1,
        extraction_status="SUCCESS",
    )
    c = ClauseORM(
        clause_id="CLAUSE-BM25-ONLY-01",
        version_number=1,
        document_id="doc_bm25_only_test",
        clause_number="Reg 2",
        text="Mandatory list of ingredients on food packaging.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    db_session.add_all([doc, c])
    db_session.flush()

    dense_engine = DenseRetrievalEngine(db=db_session)
    assert dense_engine.is_intentional_bm25 is True
    assert dense_engine.search("mandatory list ingredients") == []

    hybrid_engine = HybridRetrievalEngine(db=db_session, dense_engine=dense_engine)
    results = hybrid_engine.search("mandatory list ingredients", top_k=2)

    assert len(results) > 0
    top = results[0]
    assert top.retrieval_method == "bm25_only"
    assert top.metadata.get("dense_active") is False
    assert top.metadata.get("bm25_active") is True
    assert "Intentional BM25-only" in top.metadata.get("fallback_reason", "")


def test_preservation_of_source_and_clause_provenance(db_session: Session):
    """Verify retrieval results retain statutory document title, clause ID, number, and gap metadata."""
    doc = SourceDocumentORM(
        id="doc_provenance_check_2024",
        title="Food (Colouring Substances) Regulations 2006",
        authority="Ministry of Health",
        sha256_hash="c" * 64,
        file_path="dummy.pdf",
        file_size_bytes=1000,
        page_count=1,
        extraction_status="SUCCESS",
    )
    c = ClauseORM(
        clause_id="CLAUSE-PROV-CHECK-01",
        version_number=2,
        document_id="doc_provenance_check_2024",
        clause_number="Regulation 5(iv)",
        text="No person shall use colouring substance in fish or meat.",
        start_page=3,
        end_page=3,
        is_compilable=True,
    )
    db_session.add_all([doc, c])
    db_session.flush()

    bm25 = BM25RetrievalEngine(db_session)
    results = bm25.search("colouring substance fish", top_k=1)

    assert len(results) == 1
    res = results[0]
    assert res.clause_id == "CLAUSE-PROV-CHECK-01"
    assert res.clause_version == 2
    assert res.clause_number == "Regulation 5(iv)"
    assert res.document_id == "doc_provenance_check_2024"
    assert res.document_title == "Food (Colouring Substances) Regulations 2006"
    assert res.coverage_gap is True
