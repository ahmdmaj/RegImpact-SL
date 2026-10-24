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

def test_bm25_retrieval_operational_without_dense_or_llm(populated_db):
    """BM25 search and Hybrid RRF fallback must work normally when dense retrieval is unavailable."""
    # Hybrid engine initialized with default normal operation (dense engine has no live client)
    hybrid_engine = HybridRetrievalEngine(db=populated_db, allow_unverified=False)
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
