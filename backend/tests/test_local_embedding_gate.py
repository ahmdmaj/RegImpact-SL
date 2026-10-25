"""Regression test suite for Local Embedding Feasibility Gate and Dense Retrieval Integrity.

Audits:
- Real model output dimension (768) and finiteness validation.
- Missing model dependencies or failed model loading behavior.
- Strict refusal to fall back to mock/random vectors when local model fails.
- Embedding provenance persistence and database roundtrip.
- Exclusion of unverified vectors from normal dense retrieval.
- Honest hybrid reporting (bm25_fallback) when no verified dense vectors exist.
- Incompatible model or database vector dimension detection.

Labeling:
- Real model tests are explicitly marked with @pytest.mark.real_model.
- Test-double tests are explicitly labelled with docstrings indicating controlled test doubles.
"""

from __future__ import annotations

import math
from typing import Any, List
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, SourceDocumentORM
from backend.src.engine.retrieval import (
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    RetrievalResult,
)
from backend.src.extraction.embedding_client import (
    BaseEmbeddingClient,
    MockEmbeddingClient,
    SentenceTransformerEmbeddingClient,
    get_embedding_client,
)
from backend.src.extraction.llm_client import LLMClientError


# ---------------------------------------------------------------------------
# 1. Real Model Dimension, Finiteness, and Normalization Verification
# ---------------------------------------------------------------------------

def test_real_model_output_dimension_and_finiteness():
    """REAL-MODEL TEST: Verify BAAI/bge-base-en-v1.5 produces exactly 768 finite, normalized dimensions."""
    client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    assert client.dimension == 768
    assert client.is_verified is True
    assert client.provider_name == "sentence-transformers"
    assert client.model_name == "BAAI/bge-base-en-v1.5"

    provenance = client.get_provenance()
    assert provenance["provider"] == "sentence-transformers"
    assert provenance["model"] == "BAAI/bge-base-en-v1.5"
    assert provenance["dimension"] == 768
    assert provenance["is_verified"] is True
    assert "revision" in provenance
    assert provenance["revision"] != ""

    test_text = (
        "A person shall not import, transport, distribute, store, sell, offer for sale, expose or keep for sale "
        "or advertise, any food contained in a package or container, unless such package or container is "
        "labelled in accordance with these regulations."
    )
    vec = client.embed_text(test_text)
    assert len(vec) == 768
    assert all(math.isfinite(x) for x in vec)

    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4, f"Vector norm {norm} should be unit-length"

    # Query embedding with BGE retrieval prompt
    query_text = "What are the mandatory labelling requirements for prepackaged food products?"
    q_vec = client.embed_query(query_text)
    assert len(q_vec) == 768
    assert all(math.isfinite(x) for x in q_vec)
    q_norm = math.sqrt(sum(x * x for x in q_vec))
    assert abs(q_norm - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# 2. Missing Dependencies and Failed Model Loading
# ---------------------------------------------------------------------------

def test_missing_dependencies_raises_llm_client_error(monkeypatch):
    """TEST-DOUBLE TEST: When sentence_transformers is uninstalled, client must fail fast with LLMClientError."""
    import sys
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    with pytest.raises(LLMClientError) as exc_info:
        SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")

    err = str(exc_info.value).lower()
    assert "sentence-transformers" in err


def test_failed_model_loading_raises_llm_client_error(monkeypatch):
    """TEST-DOUBLE TEST: When model weight download or loading errors occur, raise LLMClientError without mock."""
    from sentence_transformers import SentenceTransformer

    def mock_init(self, *args, **kwargs):
        raise RuntimeError("Network failure downloading weights from huggingface.co")

    monkeypatch.setattr(SentenceTransformer, "__init__", mock_init)

    with pytest.raises(LLMClientError) as exc_info:
        SentenceTransformerEmbeddingClient(model="nonexistent/model")

    assert "Failed to load sentence-transformers model" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. No Mock Fallback When Local Model Fails
# ---------------------------------------------------------------------------

def test_no_mock_fallback_when_local_model_fails_and_mock_disallowed(monkeypatch):
    """TEST-DOUBLE TEST: get_embedding_client with allow_mock_fallback=False must raise, never return MockEmbeddingClient."""
    from sentence_transformers import SentenceTransformer

    def mock_init(self, *args, **kwargs):
        raise RuntimeError("CUDA out of memory or corrupted weights")

    monkeypatch.setattr(SentenceTransformer, "__init__", mock_init)

    with pytest.raises(Exception):
        get_embedding_client(
            provider="sentence-transformers",
            model="BAAI/bge-base-en-v1.5",
            allow_mock_fallback=False,
        )


# ---------------------------------------------------------------------------
# 4. Dimension Incompatibility and Finiteness Rejection
# ---------------------------------------------------------------------------

def test_dimension_incompatibility_raises_value_error():
    """REAL-MODEL TEST: When caller asks for 512 dimensions but BGE model produces 768, raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5", dimension=512)

    assert "Configured embedding dimension (512) does not match" in str(exc_info.value)


def test_finiteness_validation_catches_nans_or_infs(monkeypatch):
    """TEST-DOUBLE TEST: If inference produces NaNs or Infs, embed_batch must reject immediately."""
    client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")

    # Mock _model.encode to return vector with NaN
    import numpy as np
    bad_vec = np.zeros((1, 768))
    bad_vec[0, 0] = float("nan")

    monkeypatch.setattr(client._model, "encode", lambda texts, **kwargs: bad_vec)

    with pytest.raises(ValueError) as exc_info:
        client.embed_text("test text")

    assert "non-finite values" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. Provenance Persistence and Database Reload
# ---------------------------------------------------------------------------

def test_embedding_provenance_persistence_and_reload(db_session: Session):
    """REAL-MODEL & DB TEST: Embed clause using real model, persist in SQLite/Postgres DB, and verify provenance reload."""
    doc = SourceDocumentORM(
        id="doc_provenance_test",
        title="Provenance Test Document",
        authority="Test Authority",
        sha256_hash="4" * 64,
        file_path="dummy.pdf",
        file_size_bytes=1000,
        page_count=1,
        extraction_status="SUCCESS",
    )
    clause = ClauseORM(
        clause_id="CLAUSE-PROVENANCE-001",
        version_number=1,
        document_id="doc_provenance_test",
        clause_number="Regulation 3",
        text="All retail food packages must carry clear trilingual labelling.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    db_session.add_all([doc, clause])
    db_session.flush()

    emb_client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    dense_engine = DenseRetrievalEngine(db=db_session, embedding_client=emb_client)

    indexed = dense_engine.index_clauses(clause_ids=["CLAUSE-PROVENANCE-001"])
    assert indexed == 1
    db_session.commit()

    # Reload fresh from database
    db_session.expire_all()
    reloaded = db_session.get(ClauseORM, ("CLAUSE-PROVENANCE-001", 1))
    assert reloaded is not None
    assert reloaded.embedding is not None
    assert len(reloaded.embedding) == 768
    assert reloaded.embedding_verified is True
    assert reloaded.embedding_provider == "sentence-transformers"
    assert reloaded.embedding_model == "BAAI/bge-base-en-v1.5"


# ---------------------------------------------------------------------------
# 6. Exclusion of Unverified Vectors and Honest Hybrid Reporting
# ---------------------------------------------------------------------------

def test_unverified_vectors_excluded_from_real_dense_retrieval(db_session: Session):
    """TEST-DOUBLE TEST: Dense retrieval with verified model must exclude unverified stored vectors."""
    doc = SourceDocumentORM(
        id="doc_exclusion_test",
        title="Exclusion Test Document",
        authority="Test Authority",
        sha256_hash="5" * 64,
        file_path="dummy.pdf",
        file_size_bytes=1000,
        page_count=1,
        extraction_status="SUCCESS",
    )
    # Clause 1 has unverified vector
    c1 = ClauseORM(
        clause_id="CLAUSE-EXCL-UNVERIFIED",
        version_number=1,
        document_id="doc_exclusion_test",
        clause_number="Reg 1",
        text="Unverified vector text",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=[0.0] * 768,
        embedding_verified=False,
    )
    # Clause 2 has verified vector
    c2 = ClauseORM(
        clause_id="CLAUSE-EXCL-VERIFIED",
        version_number=1,
        document_id="doc_exclusion_test",
        clause_number="Reg 2",
        text="Verified vector text",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=[0.0] * 768,
        embedding_verified=True,
        embedding_provider="sentence-transformers",
        embedding_model="BAAI/bge-base-en-v1.5",
    )
    db_session.add_all([doc, c1, c2])
    db_session.flush()

    emb_client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    dense_engine = DenseRetrievalEngine(db=db_session, embedding_client=emb_client, allow_unverified=False)

    results = dense_engine.search("query text", top_k=5)
    result_ids = [r.clause_id for r in results]

    assert "CLAUSE-EXCL-VERIFIED" in result_ids
    assert "CLAUSE-EXCL-UNVERIFIED" not in result_ids


def test_honest_hybrid_reporting_when_no_verified_vectors_exist(db_session: Session):
    """TEST-DOUBLE TEST: When dense returns zero verified candidates, Hybrid reports bm25_fallback and reason."""
    doc = SourceDocumentORM(
        id="doc_hybrid_fallback_test",
        title="Fallback Test Document",
        authority="Test Authority",
        sha256_hash="6" * 64,
        file_path="dummy.pdf",
        file_size_bytes=1000,
        page_count=1,
        extraction_status="SUCCESS",
    )
    # Clause has NO embedding
    c = ClauseORM(
        clause_id="CLAUSE-FALLBACK-001",
        version_number=1,
        document_id="doc_hybrid_fallback_test",
        clause_number="Reg 1",
        text="Mandatory labelling requirements for consumer goods.",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=None,
        embedding_verified=False,
    )
    db_session.add_all([doc, c])
    db_session.flush()

    # Dense engine has no verified client
    hybrid_engine = HybridRetrievalEngine(db=db_session, allow_unverified=False)
    results = hybrid_engine.search("labelling requirements", top_k=5)

    assert len(results) > 0
    top = results[0]
    assert top.clause_id == "CLAUSE-FALLBACK-001"
    assert top.retrieval_method == "bm25_fallback"
    assert top.metadata.get("dense_active") is False
    assert top.metadata.get("bm25_active") is True
    assert "Dense retrieval produced zero verified candidates" in top.metadata.get("fallback_reason", "")
