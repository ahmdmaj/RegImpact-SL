"""Milestone 4 unit tests: Genuine RAG baselines (B0-B3) and System P full pipeline.

All tests run completely offline using MockLLMClient, MockEmbeddingClient,
and an in-memory SQLite database.
Test coverage:
  BASE-B0-001   B0 OracleBaseline evaluates scenario using oracle context and LLM.
  BASE-B0-002   B0 OracleBaseline returns UNSUPPORTED when oracle context is missing.
  BASE-B0-003   B0 OracleBaseline records LLM failure as UNSUPPORTED without crashing.
  BASE-B1-001   B1 BM25Baseline retrieves passages and generates structured result.
  BASE-B1-002   B1 BM25Baseline returns UNSUPPORTED on zero-match retrieval.
  BASE-B2-001   B2 DenseBaseline retrieves passages via dense embeddings and evaluates.
  BASE-B2-002   B2 DenseBaseline records LLM exception as UNSUPPORTED failure.
  BASE-B3-001   B3 HybridBaseline fuses BM25 and Dense with RRF and evaluates via LLM.
  BASE-P-001    SystemP full pipeline executes deterministic engine on approved rule.
  BASE-P-002    SystemP full pipeline flags coverage gap when rule is unapproved/missing.
  BASE-P-003    SystemP direct rule mode maintains Phase A backward compatibility.
  BASE-COMP-001 BenchmarkRunner runs B0, B1, B2, B3, and P under common harness.
  BASE-FAIR-001 Baseline prompt construction enforces identical schema and prompt framing.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
)
from backend.src.evaluation.baselines import (
    BASELINE_EVALUATION_SCHEMA,
    BM25Baseline,
    DenseBaseline,
    HybridBaseline,
    OracleBaseline,
    SystemP,
    construct_baseline_prompt,
)
from backend.src.evaluation.benchmark_runner import BenchmarkRunner
from backend.src.extraction.compiler import MockLLMClient
from backend.src.extraction.embedding_client import MockEmbeddingClient
from backend.src.models.domain import (
    BenchmarkScenario,
    BusinessProfile,
    EvaluationReport,
    EvaluationResult,
    OutcomeStatus,
    Product,
    ProductionCapacity,
    Rule,
    Source,
    Validity,
    AppliesIf,
    Condition,
    Obligation,
    Verification,
)


# ---------------------------------------------------------------------------
# Database & Domain Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def populated_eval_db(db_session: Session) -> Session:
    """Populate database with source documents, clauses, and approved/unapproved rules."""
    # 1. Document
    doc = SourceDocumentORM(
        id="doc_food_2024",
        sha256_hash="f" * 64,
        title="Food (Labelling and Advertising) Regulations 2024",
        authority="Food Control Administration Unit",
        file_path="backend/data/raw_sources/food_2024.pdf",
        file_size_bytes=4096,
        page_count=5,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add(doc)
    db_session.flush()

    # 2. Clause 1 (Approved rule exists)
    c1 = ClauseORM(
        clause_id="CLAUSE-REG-4",
        version_number=1,
        document_id="doc_food_2024",
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

    # 3. Clause 2 (Coverage gap: no rule in rules table)
    c2 = ClauseORM(
        clause_id="CLAUSE-REG-9",
        version_number=1,
        document_id="doc_food_2024",
        clause_number="Regulation 9",
        text="Regulation 9. Novel food ingredients shall obtain prior ministerial approval.",
        start_page=2,
        end_page=2,
        char_start=0,
        char_end=80,
        is_compilable=False,
    )

    db_session.add_all([c1, c2])
    db_session.flush()

    # 4. Compute mock dense embeddings for both clauses
    emb_client = MockEmbeddingClient(dimension=64)
    c1.embedding = emb_client.embed_text(c1.text)
    c2.embedding = emb_client.embed_text(c2.text)

    # 5. Rule for Clause 1 (APPROVED)
    r1 = RuleORM(
        rule_id="RULE-REG-4",
        clause_id="CLAUSE-REG-4",
        clause_version=1,
        outcome_type="STANDARD",
        applies_if={
            "all": [
                {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                {"field": "production_capacity.kg_per_day", "op": "gte", "value": 50},
            ]
        },
        exceptions=[],
        obligation={
            "type": "labelling",
            "text": "Display nutrition panel",
            "impact_categories": ["labelling", "packaging"],
        },
        validity={"published": "2024-01-01", "commences": "2024-06-01"},
        source={"clause": "Regulation 4", "instrument": "Food Act", "quote_span": "50 kg per day"},
        review_status="APPROVED",
    )
    db_session.add(r1)
    db_session.commit()

    return db_session


@pytest.fixture()
def sample_scenario() -> BenchmarkScenario:
    """Benchmark scenario targeting Regulation 4 with an applicable business profile."""
    return BenchmarkScenario(
        scenario_id="SCEN-M4-001",
        clause_id="Regulation 4",
        scenario_type="direct",
        business_profile=BusinessProfile(
            business_id="BIZ-TEST-01",
            activity="food_manufacturing",
            production_capacity=ProductionCapacity(value=75.0, unit="kg", per_period="day"),
        ),
        as_at_date="2024-08-01",
        gold_outcome=OutcomeStatus.APPLICABLE,
        gold_impact_categories=["labelling", "packaging"],
    )


# ---------------------------------------------------------------------------
# B0 Oracle Baseline Tests
# ---------------------------------------------------------------------------

def test_base_b0_001_oracle_evaluation(sample_scenario):
    """B0 OracleBaseline evaluates scenario using oracle context."""
    canned_llm_response = {
        "status": "APPLICABLE",
        "missing_fields": [],
        "reason": "Production capacity 75 kg/day exceeds 50 kg/day threshold in Regulation 4.",
    }
    mock_llm = MockLLMClient(canned_rule_dict=canned_llm_response)

    oracle_store = {
        "Regulation 4": (
            "Regulation 4. Every food manufacturing enterprise with capacity 50 kg/day shall label packages."
        )
    }

    baseline = OracleBaseline(context_store=oracle_store, llm_client=mock_llm)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.APPLICABLE
    assert result.rule_id == "Regulation 4"
    assert "exceeds 50 kg/day" in result.reason
    assert result.model_extra.get("method") == "oracle"
    assert len(mock_llm.call_history) == 1


def test_base_b0_002_oracle_missing_context(sample_scenario):
    """B0 OracleBaseline returns UNSUPPORTED when oracle context is missing."""
    mock_llm = MockLLMClient()
    baseline = OracleBaseline(context_store={}, llm_client=mock_llm)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.UNSUPPORTED
    assert "No oracle context found" in result.reason
    assert len(mock_llm.call_history) == 0


def test_base_b0_003_oracle_llm_failure(sample_scenario):
    """B0 OracleBaseline records LLM failure as UNSUPPORTED without raising unhandled error."""
    mock_llm = MockLLMClient(error_to_raise=RuntimeError("API quota exhausted"))
    oracle_store = {"Regulation 4": "Some legal clause text."}

    baseline = OracleBaseline(context_store=oracle_store, llm_client=mock_llm)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.UNSUPPORTED
    assert "Oracle LLM generation failed" in result.reason
    assert result.model_extra.get("failed") is True


# ---------------------------------------------------------------------------
# B1 BM25 Lexical Baseline Tests
# ---------------------------------------------------------------------------

def test_base_b1_001_bm25_pipeline(populated_eval_db, sample_scenario):
    """B1 BM25Baseline retrieves passages and generates structured response."""
    canned_llm_response = {
        "status": "APPLICABLE",
        "missing_fields": [],
        "reason": "Retrieved Regulation 4 applies to food manufacturing with 75 kg/day capacity.",
    }
    mock_llm = MockLLMClient(canned_rule_dict=canned_llm_response)
    bm25_engine = BM25RetrievalEngine(populated_eval_db)

    baseline = BM25Baseline(retrieval_engine=bm25_engine, llm_client=mock_llm, top_k=2)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.APPLICABLE
    assert result.model_extra.get("method") == "bm25"
    assert "CLAUSE-REG-4" in result.model_extra.get("retrieved_clause_ids")
    assert len(mock_llm.call_history) == 1


def test_base_b1_002_bm25_zero_matches(populated_eval_db, sample_scenario):
    """B1 BM25Baseline returns UNSUPPORTED when no passages are found."""
    mock_llm = MockLLMClient()
    bm25_engine = BM25RetrievalEngine(populated_eval_db)

    # Scenario with unmatchable nonsense query
    weird_scen = sample_scenario.model_copy(deep=True)
    weird_scen.clause_id = "xyzzy999_nonexistent_token"
    weird_scen.business_profile.activity = "unobtainium_mining"

    baseline = BM25Baseline(retrieval_engine=bm25_engine, llm_client=mock_llm)
    result = baseline.evaluate_scenario(weird_scen)

    assert result.status == OutcomeStatus.UNSUPPORTED
    assert "zero candidate passages" in result.reason


# ---------------------------------------------------------------------------
# B2 Dense Vector Baseline Tests
# ---------------------------------------------------------------------------

def test_base_b2_001_dense_pipeline(populated_eval_db, sample_scenario):
    """B2 DenseBaseline retrieves passages via dense embeddings and evaluates."""
    canned_llm_response = {
        "status": "APPLICABLE",
        "missing_fields": [],
        "reason": "Dense retrieval identified Regulation 4 as relevant; criteria satisfied.",
    }
    mock_llm = MockLLMClient(canned_rule_dict=canned_llm_response)
    emb_client = MockEmbeddingClient(dimension=64)
    dense_engine = DenseRetrievalEngine(populated_eval_db, embedding_client=emb_client)

    baseline = DenseBaseline(retrieval_engine=dense_engine, llm_client=mock_llm, top_k=2)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.APPLICABLE
    assert result.model_extra.get("method") == "dense"
    assert len(result.model_extra.get("retrieved_clause_ids")) > 0


def test_base_b2_002_dense_llm_failure(populated_eval_db, sample_scenario):
    """B2 DenseBaseline handles LLM exceptions gracefully."""
    mock_llm = MockLLMClient(error_to_raise=ValueError("Malformed JSON response"))
    emb_client = MockEmbeddingClient(dimension=64)
    dense_engine = DenseRetrievalEngine(populated_eval_db, embedding_client=emb_client)

    baseline = DenseBaseline(retrieval_engine=dense_engine, llm_client=mock_llm)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.UNSUPPORTED
    assert "Dense LLM generation failed" in result.reason
    assert result.model_extra.get("failed") is True


# ---------------------------------------------------------------------------
# B3 Hybrid RRF Baseline Tests
# ---------------------------------------------------------------------------

def test_base_b3_001_hybrid_pipeline(populated_eval_db, sample_scenario):
    """B3 HybridBaseline fuses BM25 and Dense retrieval via RRF and evaluates."""
    canned_llm_response = {
        "status": "APPLICABLE",
        "missing_fields": [],
        "reason": "Hybrid RRF ranked Regulation 4 as rank 1; applicability verified.",
    }
    mock_llm = MockLLMClient(canned_rule_dict=canned_llm_response)
    emb_client = MockEmbeddingClient(dimension=64)
    dense_engine = DenseRetrievalEngine(populated_eval_db, embedding_client=emb_client)
    bm25_engine = BM25RetrievalEngine(populated_eval_db)
    hybrid_engine = HybridRetrievalEngine(
        populated_eval_db, bm25_engine=bm25_engine, dense_engine=dense_engine, rrf_k=60
    )

    baseline = HybridBaseline(retrieval_engine=hybrid_engine, llm_client=mock_llm, top_k=2)
    result = baseline.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.APPLICABLE
    assert result.model_extra.get("method") == "hybrid_rrf"
    assert "CLAUSE-REG-4" in result.model_extra.get("retrieved_clause_ids")


# ---------------------------------------------------------------------------
# System P Full Pipeline & Coverage Gap Tests
# ---------------------------------------------------------------------------

def test_base_p_001_full_pipeline_success(populated_eval_db, sample_scenario):
    """SystemP full pipeline retrieves clause with approved rule and deterministically executes."""
    bm25_engine = BM25RetrievalEngine(populated_eval_db)
    system_p = SystemP(
        db=populated_eval_db,
        retrieval_engine=bm25_engine,
        top_k=2,
    )

    result = system_p.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.APPLICABLE
    assert result.model_extra.get("coverage_gap") is False
    assert result.model_extra.get("grounded_rule_id") == "RULE-REG-4"
    assert "impact" in result.model_extra


def test_base_p_002_coverage_gap_exposure(populated_eval_db, sample_scenario):
    """SystemP explicitly reports coverage gap when retrieved clause has no approved rule."""
    bm25_engine = BM25RetrievalEngine(populated_eval_db)
    system_p = SystemP(
        db=populated_eval_db,
        retrieval_engine=bm25_engine,
        top_k=2,
    )

    # Scenario targeting Regulation 9 (which has no rule)
    gap_scenario = sample_scenario.model_copy(deep=True)
    gap_scenario.clause_id = "Novel food ingredients Regulation 9"

    result = system_p.evaluate_scenario(gap_scenario)

    assert result.status == OutcomeStatus.UNSUPPORTED
    assert result.model_extra.get("coverage_gap") is True
    assert "System P Coverage Gap" in result.reason


def test_base_p_003_direct_rule_mode_backward_compat(sample_scenario):
    """SystemP direct rule registration mode functions identically to Phase A."""
    rule = Rule(
        rule_id="DIRECT-01",
        source=Source(
            instrument="Food Act",
            authority="FCAU",
            gazette_no="1",
            clause="Regulation 4",
            page=1,
            quote_span="Regulation 4. 50 kg/day",
        ),
        validity=Validity(published="2024-01-01", commences="2024-06-01"),
        applies_if=AppliesIf(
            all=[Condition(field="production_capacity.kg_per_day", op="gte", value=50)]
        ),
        exceptions=[],
        obligation=Obligation(type="labelling", text="Label", impact_categories=["labelling"]),
        verification=Verification(status="human_verified", extraction_model="manual", agreement=True),
    )

    system_p = SystemP(rules=rule)
    result = system_p.evaluate_scenario(sample_scenario)

    assert result.status == OutcomeStatus.APPLICABLE


# ---------------------------------------------------------------------------
# Benchmark Runner & Fairness Tests
# ---------------------------------------------------------------------------

def test_base_comp_001_benchmark_runner_multi_system(populated_eval_db, sample_scenario):
    """BenchmarkRunner executes all baselines (B0, B1, B2, B3, P) and produces EvaluationReports."""
    canned_res = {
        "status": "APPLICABLE",
        "missing_fields": [],
        "reason": "Applicable",
    }
    mock_llm = MockLLMClient(canned_rule_dict=canned_res)
    emb_client = MockEmbeddingClient(dimension=64)

    bm25 = BM25RetrievalEngine(populated_eval_db)
    dense = DenseRetrievalEngine(populated_eval_db, embedding_client=emb_client)
    hybrid = HybridRetrievalEngine(populated_eval_db, bm25_engine=bm25, dense_engine=dense)

    b0 = OracleBaseline(
        context_store={"Regulation 4": "Regulation 4 text."}, llm_client=mock_llm
    )
    b1 = BM25Baseline(retrieval_engine=bm25, llm_client=mock_llm)
    b2 = DenseBaseline(retrieval_engine=dense, llm_client=mock_llm)
    b3 = HybridBaseline(retrieval_engine=hybrid, llm_client=mock_llm)
    p = SystemP(db=populated_eval_db, retrieval_engine=hybrid)

    runner = BenchmarkRunner(scenarios=[sample_scenario])

    for system in [b0, b1, b2, b3, p]:
        report = runner.run(system)
        assert isinstance(report, EvaluationReport)
        assert report.total_scenarios == 1
        assert report.accuracy == 1.0
        assert report.system_name == system.name


def test_base_fair_001_prompt_and_schema_uniformity(sample_scenario):
    """Prompt construction and output schema are identical and well-formed."""
    prompt = construct_baseline_prompt("Sample legal context text.", sample_scenario)

    assert "REGULATORY CONTEXT:" in prompt
    assert "BUSINESS PROFILE:" in prompt
    assert "AS-AT ASSESSMENT DATE:" in prompt
    assert "Sample legal context text." in prompt
    assert "food_manufacturing" in prompt

    # Verify target schema definition
    assert BASELINE_EVALUATION_SCHEMA["type"] == "object"
    assert "status" in BASELINE_EVALUATION_SCHEMA["required"]
    assert "APPLICABLE" in BASELINE_EVALUATION_SCHEMA["properties"]["status"]["enum"]
    assert "UNSUPPORTED" in BASELINE_EVALUATION_SCHEMA["properties"]["status"]["enum"]
