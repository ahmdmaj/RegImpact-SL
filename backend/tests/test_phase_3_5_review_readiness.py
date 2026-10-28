"""Focused Verification Suite for Phase 3.5: Human Review Workflow & Benchmark Readiness Gate.

Validates:
  P35-GATE-01  Pending rules cannot become gold merely by passing technical verification / compiler agreement.
  P35-GATE-02  Role-based gold gating: PRIMARY_ANNOTATOR and SECONDARY_ANNOTATOR cannot mark is_gold_rule=True;
               only EXPERT_ADJUDICATOR can set is_gold_rule=True.
  P35-GATE-03  Invalid reviewer roles and decision tokens are strictly rejected.
  P35-GATE-04  Blank or whitespace-only review rationales are rejected.
  P35-GATE-05  Audit trail immutability and history preservation across multiple review passes.
  P35-GATE-06  Review queue isolation: only PENDING_REVIEW / DRAFT rules are returned in the queue.
  P35-GATE-07  FastAPI approve endpoint supports explicit reviewer_role and records it in the audit trail.
  P35-GATE-08  All 30 benchmark scenarios reference authentic clauses and verified SHA-256 hashes in PostgreSQL.
  P35-GATE-09  Zero-gold benchmark invariant: all 30 candidate scenarios have is_gold_scenario=False and is_gold_rule=False.
  P35-GATE-10  Clause-level dataset partitioning enforces 100% disjoint clause sets and preserves paired scenarios.
  P35-GATE-11  Truthfulness audit: authentic production DB reflects zero fabricated second-annotator or expert sign-offs.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.review import (
    DECISION_APPROVED,
    DECISION_REJECTED,
    InvalidReviewDecisionError,
    InvalidReviewerRoleError,
    ROLE_EXPERT_ADJUDICATOR,
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_SECONDARY_ANNOTATOR,
    ReviewService,
)
from backend.src.evaluation.benchmark_validator import (
    AUTHENTIC_SOURCE_HASHES,
    KNOWN_AUTHENTIC_RULES,
    load_benchmark_scenarios,
    validate_benchmark_slice,
)
from backend.src.evaluation.dataset_split import split_scenarios_by_clause
from backend.src.extraction.compiler import MockLLMClient, RuleCompiler
from backend.src.main import app
from backend.src.models.domain import AppliesIf, BenchmarkScenario, Condition, Obligation, Rule, Source, Validity, Verification
from backend.tests.conftest import LIVE_DATABASE_URL

MULTI_SLICE_PATH = Path("backend/data/benchmark/multi_group_benchmark_slice.jsonl")

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
        engine = create_engine_from_url(DATABASE_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


POSTGRES_AVAILABLE = _can_connect_to_postgres()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def base_rule() -> Rule:
    """Standard baseline verified rule."""
    quote = (
        "Published on 2026-01-01, commences 2026-06-01. "
        "Regulation 4. Food manufacturers with capacity of 50 kg/day shall label packages."
    )
    return Rule(
        rule_id="RULE-P35-BASE-01",
        source=Source(
            instrument="Food Act Regulations 2026",
            authority="FCAU",
            gazette_no="2026/01",
            clause="Regulation 4",
            page=1,
            quote_span=quote,
        ),
        validity=Validity(published="2026-01-01", commences="2026-06-01"),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="production_capacity.kg_per_day", op="gte", value=50),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="labelling",
            text="Label all packages with nutrition facts.",
            impact_categories=["labelling", "packaging"],
        ),
        verification=Verification(
            status="verified",
            extraction_model="mock-v1",
            agreement=True,
        ),
    )


@pytest.fixture(scope="module")
def multi_group_scenarios() -> List[BenchmarkScenario]:
    """Load the candidate benchmark slice."""
    assert MULTI_SLICE_PATH.exists(), f"Benchmark slice file missing at {MULTI_SLICE_PATH}"
    return load_benchmark_scenarios(MULTI_SLICE_PATH)


@pytest.fixture()
def live_db():
    """Session to the live PostgreSQL database."""
    if not POSTGRES_AVAILABLE:
        pytest.skip("Live PostgreSQL daemon is not reachable.")
    engine = create_engine_from_url(DATABASE_URL)
    session_factory = get_session_factory(engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def review_rule_fixture(db_session: Session) -> RuleORM:
    """Isolated test fixture in SQLite test session."""
    doc = SourceDocumentORM(
        id="doc_test_p35",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        title="Test Regulation P35",
        authority="FCAU",
        file_path="backend/data/raw_sources/test.pdf",
        file_size_bytes=1024,
        page_count=1,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add(doc)
    db_session.flush()

    clause = ClauseORM(
        clause_id="clause_p35_01",
        version_number=1,
        document_id="doc_test_p35",
        clause_number="5",
        text="All packaged food must bear clear labeling.",
        start_page=1,
        end_page=1,
        char_start=0,
        char_end=42,
        is_compilable=True,
    )
    db_session.add(clause)
    db_session.flush()

    rule = RuleORM(
        rule_id="RULE-P35-TEST-01",
        clause_id="clause_p35_01",
        clause_version=1,
        outcome_type="STANDARD",
        applies_if={"all": [{"field": "activity", "op": "eq", "value": "food_manufacturing"}]},
        obligation={"type": "labelling", "text": "Apply package label"},
        validity={"published": "2026-01-01"},
        source={"clause": "5", "quote_span": "All packaged food must bear clear labeling."},
        review_status="PENDING_REVIEW",
        is_gold_rule=False,
    )
    db_session.add(rule)
    db_session.commit()
    return rule


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_p35_gate_01_technical_verification_cannot_create_gold(base_rule):
    """P35-GATE-01: Technical verification / dual-pass agreement does NOT create a gold rule."""
    rule_dict = base_rule.model_dump()
    raw_text = base_rule.source.quote_span
    metadata = {
        "instrument": base_rule.source.instrument,
        "authority": base_rule.source.authority,
        "gazette_no": base_rule.source.gazette_no,
        "clause": base_rule.source.clause,
        "page": base_rule.source.page,
    }

    mock_client = MockLLMClient(canned_rule_dict=rule_dict)
    compiler = RuleCompiler(llm_client=mock_client)

    result = compiler.compile_clause_with_agreement(raw_text, metadata)
    assert result.cross_agreement is True
    # Compiler sets initial review_status, but must NEVER designate is_gold_rule
    assert result.rule is not None
    # Verify the rule domain model does not have is_gold_rule=True
    verification = getattr(result.rule, "verification", None)
    assert getattr(result.rule, "is_gold_rule", False) is False


def test_p35_gate_02_role_based_gold_gating(db_session, review_rule_fixture):
    """P35-GATE-02: Only EXPERT_ADJUDICATOR can set is_gold_rule=True."""
    service = ReviewService(db_session)

    # 1. Primary Annotator approval
    updated_primary = service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="primary_annotator_1",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Primary annotation verified against clause text.",
    )
    assert updated_primary.review_status == "APPROVED"
    assert updated_primary.is_gold_rule is False

    # 2. Secondary Annotator approval
    updated_secondary = service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="secondary_annotator_2",
        reviewer_role=ROLE_SECONDARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Independent second annotator confirmed agreement.",
    )
    assert updated_secondary.review_status == "APPROVED"
    assert updated_secondary.is_gold_rule is False

    # 3. Expert Adjudicator approval -> triggers gold designation
    updated_expert = service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="senior_legal_expert",
        reviewer_role=ROLE_EXPERT_ADJUDICATOR,
        decision=DECISION_APPROVED,
        rationale="Final legal adjudication signed off by regulatory counsel.",
    )
    assert updated_expert.review_status == "APPROVED"
    assert updated_expert.is_gold_rule is True


def test_p35_gate_03_invalid_reviewer_roles_and_decisions_rejected(db_session, review_rule_fixture):
    """P35-GATE-03: Invalid roles and decision tokens raise explicit domain exceptions."""
    service = ReviewService(db_session)

    # Invalid role
    with pytest.raises(InvalidReviewerRoleError):
        service.submit_review(
            rule_id="RULE-P35-TEST-01",
            reviewer_id="intern_1",
            reviewer_role="UNAUTHORISED_INTERN",
            decision=DECISION_APPROVED,
            rationale="Approved by intern",
        )

    # Invalid decision token
    with pytest.raises(InvalidReviewDecisionError):
        service.submit_review(
            rule_id="RULE-P35-TEST-01",
            reviewer_id="annotator_1",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision="PENDING_MAYBE",
            rationale="Unsure about decision",
        )


def test_p35_gate_04_blank_rationale_rejected(db_session, review_rule_fixture):
    """P35-GATE-04: Blank or whitespace-only rationales are rejected."""
    service = ReviewService(db_session)
    with pytest.raises(ValueError) as exc:
        service.submit_review(
            rule_id="RULE-P35-TEST-01",
            reviewer_id="annotator_1",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision=DECISION_APPROVED,
            rationale="    \n   ",
        )
    assert "rationale must be provided" in str(exc.value).lower()


def test_p35_gate_05_audit_trail_preservation(db_session, review_rule_fixture):
    """P35-GATE-05: Audit trail preserves full history across multiple reviews."""
    service = ReviewService(db_session)

    service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="annotator_1",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_REJECTED,
        rationale="Initial pass rejected: missing unit qualification.",
    )

    service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="annotator_2",
        reviewer_role=ROLE_SECONDARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Second review verified with amended units.",
    )

    service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="legal_expert",
        reviewer_role=ROLE_EXPERT_ADJUDICATOR,
        decision=DECISION_APPROVED,
        rationale="Final legal adjudication confirmed.",
    )

    audits = service.get_audit_trail("RULE-P35-TEST-01")
    assert len(audits) == 3
    assert audits[0].decision == "REJECTED"
    assert audits[0].reviewer_role == ROLE_PRIMARY_ANNOTATOR
    assert audits[1].decision == "APPROVED"
    assert audits[1].reviewer_role == ROLE_SECONDARY_ANNOTATOR
    assert audits[2].decision == "APPROVED"
    assert audits[2].reviewer_role == ROLE_EXPERT_ADJUDICATOR


def test_p35_gate_06_review_queue_isolation(db_session, review_rule_fixture):
    """P35-GATE-06: Review queue strictly excludes already approved or rejected rules."""
    service = ReviewService(db_session)

    # Initially in queue
    pending = service.get_pending_reviews()
    assert any(r.rule_id == "RULE-P35-TEST-01" for r in pending)

    # Approve it
    service.submit_review(
        rule_id="RULE-P35-TEST-01",
        reviewer_id="annotator_1",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Approved",
    )

    # Excluded from queue
    pending_after = service.get_pending_reviews()
    assert not any(r.rule_id == "RULE-P35-TEST-01" for r in pending_after)


def test_p35_gate_07_api_approve_endpoint_with_reviewer_role(client: TestClient, db_session: Session, review_rule_fixture):
    """P35-GATE-07: POST /admin/reviews/{rule_id}/approve propagates reviewer_role correctly."""
    from backend.src.db.session import get_db

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        payload = {
            "reviewer_id": "test_secondary_reviewer",
            "reviewer_role": "SECONDARY_ANNOTATOR",
            "rationale": "Independent second annotator agreement confirmed.",
        }
        response = client.post("/admin/reviews/RULE-P35-TEST-01/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["review_status"] == "APPROVED"

        # Check audit record in DB
        audit = (
            db_session.query(HumanReviewAuditORM)
            .filter_by(rule_id="RULE-P35-TEST-01")
            .order_by(HumanReviewAuditORM.reviewed_at.desc())
            .first()
        )
        assert audit is not None
        assert audit.reviewer_id == "test_secondary_reviewer"
        assert audit.reviewer_role == "SECONDARY_ANNOTATOR"
        assert audit.decision == "APPROVED"
    finally:
        app.dependency_overrides.clear()


def test_p35_gate_08_benchmark_clause_grounding(live_db: Session, multi_group_scenarios: List[BenchmarkScenario]):
    """P35-GATE-08: All 30 scenarios reference authentic clauses and verified source hashes in PostgreSQL."""
    scenario_clauses = {s.clause_id for s in multi_group_scenarios}
    assert len(scenario_clauses) == 6

    authentic_clauses = (
        live_db.query(ClauseORM)
        .filter(ClauseORM.is_synthetic == False)  # noqa: E712
        .all()
    )
    auth_numbers = {c.clause_number.lower() for c in authentic_clauses if c.clause_number}

    for cid in scenario_clauses:
        assert cid.lower() in auth_numbers, f"Clause {cid} not found in authentic PostgreSQL clauses"

    # Verify source hashes
    for sc in multi_group_scenarios:
        extra = sc.model_extra or {}
        h = extra.get("source_hash")
        assert h in AUTHENTIC_SOURCE_HASHES, f"Scenario {sc.scenario_id} references unverified hash {h}"


def test_p35_gate_09_provisional_scenarios_remain_provisional(multi_group_scenarios: List[BenchmarkScenario]):
    """P35-GATE-09: Validation confirms zero gold scenarios and zero gold rules."""
    rep = validate_benchmark_slice(
        multi_group_scenarios,
        known_rules=KNOWN_AUTHENTIC_RULES,
        known_sources=set(AUTHENTIC_SOURCE_HASHES.keys()),
        enforce_provisional=True,
    )
    assert rep.is_valid is True
    assert rep.gold_scenarios_count == 0
    assert rep.provisional_scenarios_count == 30
    for s in multi_group_scenarios:
        extra = s.model_extra or {}
        assert extra.get("is_gold_scenario") is False
        assert extra.get("is_gold_rule") is False


def test_p35_gate_10_clause_disjoint_dataset_partitioning(multi_group_scenarios: List[BenchmarkScenario]):
    """P35-GATE-10: Dataset partitioning enforces zero clause leakage and preserves all paired scenarios."""
    for seed in [1, 7, 42, 99, 1234]:
        train_set, test_set = split_scenarios_by_clause(
            multi_group_scenarios,
            test_ratio=0.3,
            random_seed=seed,
        )
        assert len(train_set) + len(test_set) == len(multi_group_scenarios)

        train_clauses = {s.clause_id for s in train_set}
        test_clauses = {s.clause_id for s in test_set}
        overlap = train_clauses & test_clauses
        assert len(overlap) == 0, f"Clause leakage on seed {seed}: {overlap}"

        train_pairs = {s.pair_id for s in train_set if s.pair_id}
        test_pairs = {s.pair_id for s in test_set if s.pair_id}
        pair_leakage = train_pairs & test_pairs
        assert len(pair_leakage) == 0, f"Pair broken across splits on seed {seed}: {pair_leakage}"


def test_p35_gate_11_live_production_truthfulness(live_db: Session):
    """P35-GATE-11: Verify truthful database state without fabricated reviews.

    Verifies:
      1. Exactly 13 authentic rules exist (2 APPROVED by primary annotator, 11 PENDING_REVIEW including Phase 4.3 compilation).
      2. Exactly 0 authentic rules have is_gold_rule=True.
      3. Exactly 0 authentic rules have SECONDARY_ANNOTATOR or EXPERT_ADJUDICATOR audits.
      4. Exactly 11 candidate rules have zero human review audits.
    """
    authentic_rules = (
        live_db.query(RuleORM)
        .filter(RuleORM.is_synthetic == False)  # noqa: E712
        .all()
    )
    assert len(authentic_rules) == 13, f"Expected 13 authentic rules, found {len(authentic_rules)}"

    gold_rules = [r for r in authentic_rules if r.is_gold_rule]
    assert len(gold_rules) == 0, f"Found unexpected gold rules in production: {[r.rule_id for r in gold_rules]}"

    approved = [r for r in authentic_rules if r.review_status == "APPROVED"]
    pending = [r for r in authentic_rules if r.review_status == "PENDING_REVIEW"]
    assert len(approved) == 2
    assert len(pending) == 11

    # Check audits
    rule_ids = {r.rule_id for r in authentic_rules}
    audits = (
        live_db.query(HumanReviewAuditORM)
        .filter(HumanReviewAuditORM.rule_id.in_(rule_ids))
        .all()
    )
    assert len(audits) == 2, f"Expected exactly 2 audits for authentic rules, found {len(audits)}"
    for a in audits:
        assert a.reviewer_role == ROLE_PRIMARY_ANNOTATOR
        assert a.rule_id in {"RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"}
        assert "independent legal expert adjudication is pending" in a.rationale.lower()
