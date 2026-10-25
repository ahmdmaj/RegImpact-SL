"""Focused Integrity Gate Regression Suite.

Verifies:
  1. Mock-derived benchmark results are quarantined and cannot be reported as valid empirical findings.
  2. The benchmark runner fails clearly when required live dependencies are missing without silent mock substitution.
  3. Unverified or mock-derived stored embeddings cannot silently enter normal dense retrieval.
  4. Missing live providers produce explicit, understandable errors when allow_mock_fallback is False.
  5. BM25 and deterministic analysis remain 100% operational when dense retrieval or external LLMs are unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.src.db.models import ClauseORM, SourceDocumentORM
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
)
from backend.src.extraction.embedding_client import (
    MockEmbeddingClient,
    get_embedding_client,
)
from backend.src.extraction.llm_client import (
    LLMAuthenticationError,
    MockLLMClient,
    get_llm_client,
)
from backend.src.main import app
from backend.src.models.domain import BenchmarkScenario, OutcomeStatus
from backend.src.scripts.run_experiments import run_full_experiments


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Mock-Derived Benchmark Results Quarantine
# ---------------------------------------------------------------------------

def test_mock_derived_benchmark_results_quarantined(client: TestClient):
    """Verify that results.json is marked as invalidated mock-derived run and cannot be presented as empirical."""
    results_path = Path("backend/data/evaluation/results.json")
    if not results_path.exists():
        results_path = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "results.json"

    assert results_path.exists(), "results.json must exist"
    data = json.loads(results_path.read_text(encoding="utf-8"))

    # Must be explicitly invalidated
    assert data.get("is_empirical_result") is False
    assert data.get("status") == "INVALIDATED_MOCK_DERIVED_RUN"
    assert "quarantine_notice" in data
    assert "INVALIDATED" in data["quarantine_notice"]

    # Verify archival copy exists
    archive_path = results_path.parent / "archived_mock_results.json"
    assert archive_path.exists(), "Archival copy of mock results must be preserved"

    # API endpoint must also surface quarantine status
    res = client.get("/evaluation/results")
    assert res.status_code == 200
    api_data = res.json()
    assert api_data.get("is_empirical_result") is False
    assert api_data.get("status") == "INVALIDATED_MOCK_DERIVED_RUN"


# ---------------------------------------------------------------------------
# 2. Benchmark Runner Fails Without Silent Simulation
# ---------------------------------------------------------------------------

def test_benchmark_runner_fails_clearly_without_live_dependencies(db_session):
    """Benchmark runner must refuse to generate empirical results when live dependencies are absent."""
    scenario = BenchmarkScenario(
        scenario_id="SCEN-INT-001",
        scenario_type="direct_applicability",
        clause_id="CLAUSE-TEST-001",
        business_profile={"activity": "food_manufacturing"},
        gold_outcome=OutcomeStatus.APPLICABLE,
        description="Integrity test scenario",
        as_at_date="2026-08-01",
    )

    # Calling without live credentials and without allow_mock must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        run_full_experiments(
            scenarios=[scenario],
            db_session=db_session,
            allow_mock=False,
        )

    err = str(exc_info.value)
    assert "Live" in err or "credentials" in err
    assert "allow_mock=True" in err


# ---------------------------------------------------------------------------
# 3. Unverified Embeddings Excluded from Normal Dense Retrieval
# ---------------------------------------------------------------------------

def test_unverified_stored_embeddings_excluded_from_normal_dense_retrieval(db_session):
    """Unverified or mock-derived embeddings must be excluded from dense retrieval in normal operation."""
    doc = SourceDocumentORM(
        id="doc_integrity_test",
        title="Integrity Test Document",
        authority="Test Authority",
        sha256_hash="3333333333333333333333333333333333333333333333333333333333333333",
        file_path="dummy.pdf",
        file_size_bytes=100,
        page_count=1,
        extraction_status="SUCCESS",
    )
    db_session.add(doc)
    db_session.flush()

    # Clause 1: Has an unverified embedding (e.g. from MockEmbeddingClient or unestablished provenance)
    c_unverified = ClauseORM(
        clause_id="CLAUSE-UNVERIFIED-001",
        version_number=1,
        document_id="doc_integrity_test",
        clause_number="Regulation 1",
        text="Unverified clause with mock vector.",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=[0.5] * 128,
        embedding_verified=False,
    )
    # Clause 2: Has a verified embedding from an authenticated provider
    c_verified = ClauseORM(
        clause_id="CLAUSE-VERIFIED-001",
        version_number=1,
        document_id="doc_integrity_test",
        clause_number="Regulation 2",
        text="Verified clause with authenticated vector.",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=[0.5] * 128,
        embedding_verified=True,
    )
    db_session.add_all([c_unverified, c_verified])
    db_session.flush()

    # In normal operation mode (allow_unverified=False), DenseRetrievalEngine must filter out c_unverified
    engine = DenseRetrievalEngine(db=db_session, allow_unverified=False)
    query_vec = [0.5] * 128

    results = engine._search_in_memory_fallback(query_vec, top_k=10)
    result_ids = [r.clause_id for r in results]

    assert "CLAUSE-VERIFIED-001" in result_ids
    assert "CLAUSE-UNVERIFIED-001" not in result_ids, "Unverified clause must NOT enter normal dense retrieval!"

    # Furthermore, MockEmbeddingClient must be rejected during normal operation search
    engine_with_mock = DenseRetrievalEngine(
        db=db_session,
        embedding_client=MockEmbeddingClient(dimension=128),
        allow_unverified=False,
    )
    normal_results = engine_with_mock.search("test query", top_k=5)
    assert normal_results == [], "MockEmbeddingClient search must return empty in normal operation"


# ---------------------------------------------------------------------------
# 4. Explicit Error Behavior for Missing Live Providers
# ---------------------------------------------------------------------------

def test_missing_live_providers_produce_explicit_errors(monkeypatch):
    """When allow_mock_fallback=False, missing API keys must raise LLMAuthenticationError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    with pytest.raises(LLMAuthenticationError):
        get_llm_client(allow_mock_fallback=False)

    with pytest.raises(LLMAuthenticationError):
        get_embedding_client(allow_mock_fallback=False)


# ---------------------------------------------------------------------------
# 5. BM25 Operational Without Dense Retrieval or LLM
# ---------------------------------------------------------------------------

def test_bm25_retrieval_operational_without_dense_or_llm(db_session):
    """BM25 search and Hybrid RRF fallback must work normally when dense retrieval is unavailable."""
    doc = SourceDocumentORM(
        id="doc_food_act_test",
        sha256_hash="f" * 64,
        title="Food Labelling Regulations Test",
        authority="FCAU",
        file_path="backend/data/raw_sources/food_test.pdf",
        file_size_bytes=1000,
        page_count=2,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add(doc)
    db_session.flush()

    c1 = ClauseORM(
        clause_id="CLAUSE-FOOD-004",
        version_number=1,
        document_id="doc_food_act_test",
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
    db_session.add(c1)
    db_session.flush()

    # Hybrid engine initialized with default normal operation (dense engine has no live client)
    hybrid_engine = HybridRetrievalEngine(db=db_session, allow_unverified=False)
    assert hybrid_engine.dense_engine.embedding_client is None

    results = hybrid_engine.search("nutrition information panel", top_k=2)
    assert len(results) > 0
    assert results[0].clause_id == "CLAUSE-FOOD-004"
    assert "nutrition information panel" in results[0].text.lower()


# ---------------------------------------------------------------------------
# 6. Deterministic Analysis Works Grounded Without External Providers
# ---------------------------------------------------------------------------

def test_deterministic_analysis_succeeds_without_live_llm_or_dense_embeddings(client: TestClient):
    """POST /analysis executes deterministic rules and grounded summary without external LLMs."""
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-PROD-RETAIL-001",
            "activity": "food_manufacturing",
            "employee_count": 10,
            "packaged_in_presence_of_purchaser": False,
            "products": [
                {
                    "name": "Super Cracker Biscuits",
                    "category": "biscuits",
                    "prepackaged": True,
                    "market_channel": "retail",
                    "purchaser_present": False,
                }
            ],
            "market": {"b2b_only": False},
        },
        "clause_ids": ["RULE-FCAU-2494-47-REG-3"],
        "as_at_date": "2026-08-01",
    }

    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["applicable_rules_count"] == 1
    assert data["evaluations"][0]["rule_id"] == "RULE-FCAU-2494-47-REG-3"
    assert data["evaluations"][0]["status"] == OutcomeStatus.APPLICABLE.value

    # Narrative summary must be grounded in facts, not mock text
    summary = data.get("narrative_summary", "")
    assert summary is not None
    assert "Mock generated text explanation." not in summary
    assert "applicable" in summary.lower() or "regulatory" in summary.lower()


# ---------------------------------------------------------------------------
# 7. Mock/Manual Vectors Cannot Be Marked Verified
# ---------------------------------------------------------------------------

def test_mock_and_manual_vectors_cannot_be_marked_verified(db_session):
    """Mock-derived or manually constructed vectors must not receive embedding_verified=True."""
    mock_client = MockEmbeddingClient(dimension=768)
    assert mock_client.is_verified is False
    assert mock_client.provider_name == "mock"

    doc = SourceDocumentORM(
        id="doc_provenance_gate",
        title="Provenance Test Doc",
        authority="Test",
        sha256_hash="5555555555555555555555555555555555555555555555555555555555555555",
        file_path="dummy.pdf",
        file_size_bytes=100,
        page_count=1,
    )
    db_session.add(doc)
    db_session.flush()

    clause = ClauseORM(
        clause_id="CLAUSE-MOCK-PROV-001",
        version_number=1,
        document_id="doc_provenance_gate",
        clause_number="Reg 1",
        text="Clause text for mock indexing test.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    db_session.add(clause)
    db_session.flush()

    engine = DenseRetrievalEngine(db=db_session, embedding_client=mock_client, allow_unverified=True)
    indexed = engine.index_clauses()
    assert indexed == 1

    db_session.refresh(clause)
    assert clause.embedding is not None
    assert clause.embedding_verified is False, "MockEmbeddingClient indexing MUST NOT mark embedding_verified=True"
    assert clause.embedding_provider == "mock"


# ---------------------------------------------------------------------------
# 8. Incompatible Model Dimensions Rejected
# ---------------------------------------------------------------------------

def test_embedding_dimension_mismatch_rejected(db_session):
    """Vectors with incompatible dimensions (e.g. 128 != 768) must be rejected."""
    class BadDimClient(MockEmbeddingClient):
        def embed_batch(self, texts):
            return [[0.1] * 128 for _ in texts]
        def embed_text(self, text):
            return [0.1] * 128

    doc = SourceDocumentORM(
        id="doc_dim_gate",
        title="Dimension Gate Test Doc",
        authority="Test",
        sha256_hash="6666666666666666666666666666666666666666666666666666666666666666",
        file_path="dummy.pdf",
        file_size_bytes=100,
        page_count=1,
    )
    db_session.add(doc)
    db_session.flush()

    clause = ClauseORM(
        clause_id="CLAUSE-DIM-001",
        version_number=1,
        document_id="doc_dim_gate",
        clause_number="Reg Dim",
        text="Clause text for dimension test.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    db_session.add(clause)
    db_session.flush()

    engine = DenseRetrievalEngine(db=db_session, embedding_client=BadDimClient(dimension=128), target_dimension=768, allow_unverified=True)
    with pytest.raises(ValueError) as exc_info:
        engine.index_clauses()
    assert "dimension mismatch" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 9. Provider Failure Does Not Produce Fabricated Vectors
# ---------------------------------------------------------------------------

def test_provider_failure_does_not_produce_fabricated_vector(db_session):
    """When embedding generation fails, no fabricated vector is silently returned or persisted."""
    class FailingClient(MockEmbeddingClient):
        def embed_batch(self, texts):
            from backend.src.extraction.llm_client import LLMRateLimitError
            raise LLMRateLimitError("Live embedding provider quota exhausted (HTTP 429).")

    doc = SourceDocumentORM(
        id="doc_fail_gate",
        title="Failure Gate Doc",
        authority="Test",
        sha256_hash="7777777777777777777777777777777777777777777777777777777777777777",
        file_path="dummy.pdf",
        file_size_bytes=100,
        page_count=1,
    )
    db_session.add(doc)
    db_session.flush()

    clause = ClauseORM(
        clause_id="CLAUSE-FAIL-001",
        version_number=1,
        document_id="doc_fail_gate",
        clause_number="Reg Fail",
        text="Clause text for failure test.",
        start_page=1,
        end_page=1,
        is_compilable=True,
    )
    db_session.add(clause)
    db_session.flush()

    engine = DenseRetrievalEngine(db=db_session, embedding_client=FailingClient(), allow_unverified=True)
    from backend.src.extraction.llm_client import LLMRateLimitError
    with pytest.raises(LLMRateLimitError):
        engine.index_clauses()

    db_session.refresh(clause)
    assert clause.embedding is None, "Failed embedding operation must NOT save fabricated vector!"


# ---------------------------------------------------------------------------
# 10. Embedding Provenance Survives Persistence and Reload
# ---------------------------------------------------------------------------

def test_embedding_provenance_persisted_and_reloaded(db_session):
    """Clause embedding provenance (provider, model, verified status) persists and reloads correctly."""
    doc = SourceDocumentORM(
        id="doc_prov_reload",
        title="Reload Test Doc",
        authority="Test",
        sha256_hash="8888888888888888888888888888888888888888888888888888888888888888",
        file_path="dummy.pdf",
        file_size_bytes=100,
        page_count=1,
    )
    db_session.add(doc)
    db_session.flush()

    vec = [0.0] * 768
    vec[42] = 1.0

    clause = ClauseORM(
        clause_id="CLAUSE-PROV-RELOAD-001",
        version_number=1,
        document_id="doc_prov_reload",
        clause_number="Reg Prov",
        text="Clause text for provenance reload test.",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=vec,
        embedding_verified=True,
        embedding_provider="gemini",
        embedding_model="text-embedding-004",
    )
    db_session.add(clause)
    db_session.commit()

    # Query back
    reloaded = db_session.query(ClauseORM).filter_by(clause_id="CLAUSE-PROV-RELOAD-001").one()
    assert reloaded.embedding_verified is True
    assert reloaded.embedding_provider == "gemini"
    assert reloaded.embedding_model == "text-embedding-004"
    assert len(reloaded.embedding) == 768


# ---------------------------------------------------------------------------
# 11. Hybrid Retrieval Truthful Method Reporting
# ---------------------------------------------------------------------------

def test_hybrid_retrieval_truthful_method_reporting(db_session):
    """Hybrid retrieval must report 'hybrid_rrf' only when both rankers contribute, and 'bm25_fallback' otherwise."""
    doc = SourceDocumentORM(
        id="doc_hybrid_truth",
        title="Hybrid Truth Doc",
        authority="Test",
        sha256_hash="9999999999999999999999999999999999999999999999999999999999999999",
        file_path="dummy.pdf",
        file_size_bytes=100,
        page_count=1,
    )
    db_session.add(doc)
    db_session.flush()

    vec = [0.0] * 768
    vec[0] = 1.0

    c1 = ClauseORM(
        clause_id="CLAUSE-HYB-TRUTH-001",
        version_number=1,
        document_id="doc_hybrid_truth",
        clause_number="Reg 1",
        text="Mandatory dairy manufacturing hygiene standard regulation.",
        start_page=1,
        end_page=1,
        is_compilable=True,
        embedding=vec,
        embedding_verified=True,
    )
    db_session.add(c1)
    db_session.commit()

    # Case A: Dense engine has no verified client (dense yields 0) -> bm25_fallback
    hybrid_fallback = HybridRetrievalEngine(db=db_session, allow_unverified=False)
    assert hybrid_fallback.dense_engine.embedding_client is None

    res_fallback = hybrid_fallback.search("dairy manufacturing hygiene standard", top_k=2)
    assert len(res_fallback) > 0
    assert res_fallback[0].retrieval_method == "bm25_fallback"
    assert res_fallback[0].metadata.get("dense_active") is False
    assert res_fallback[0].metadata.get("bm25_active") is True
    assert "Dense retrieval produced zero verified candidates" in res_fallback[0].metadata.get("fallback_reason", "")

    # Case B: Both BM25 and dense return candidates -> hybrid_rrf
    from backend.src.extraction.embedding_client import BaseEmbeddingClient
    class VerifiedTestClient(BaseEmbeddingClient):
        @property
        def dimension(self):
            return 768
        @property
        def is_verified(self):
            return True
        @property
        def provider_name(self):
            return "verified-test"
        @property
        def model_name(self):
            return "test-model-768"
        def embed_text(self, text):
            return vec

    dense_active = DenseRetrievalEngine(db=db_session, embedding_client=VerifiedTestClient(), allow_unverified=False)
    hybrid_active = HybridRetrievalEngine(db=db_session, dense_engine=dense_active, allow_unverified=False)

    res_active = hybrid_active.search("dairy manufacturing hygiene standard", top_k=2)
    assert len(res_active) > 0
    assert res_active[0].retrieval_method == "hybrid_rrf"
    assert res_active[0].metadata.get("dense_active") is True
    assert res_active[0].metadata.get("bm25_active") is True
    assert res_active[0].metadata.get("fallback_reason") is None


# ---------------------------------------------------------------------------
# 12. Authenticated Gazette SHA-256 Hash Strictly Enforced
# ---------------------------------------------------------------------------

def test_authenticated_gazette_hash_strictly_enforced():
    """Verify that the authentic Gazette 2494/47 hash is strictly enforced and matches disk."""
    import hashlib
    pdf_path = Path("backend/data/raw_sources/2494-47_E.pdf")
    assert pdf_path.exists(), "Authentic Gazette PDF must exist"

    file_bytes = pdf_path.read_bytes()
    assert len(file_bytes) == 424172, "File size must exactly match official 424,172 bytes"

    actual_hash = hashlib.sha256(file_bytes).hexdigest()
    expected_hash = "83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054"
    typo_hash = "9fa733d3170e70a1a0e08f516a3bc89f6b4d3f3fdbf3cf8c7d0e49bb493e62dd"

    assert actual_hash == expected_hash, f"Actual hash {actual_hash} does not match expected {expected_hash}"
    assert actual_hash != typo_hash, "Actual hash must not match the documentation typo"

