"""Milestone 2 unit tests: Cross-extraction agreement, review state machine, and audit trail.

Covers:
  AGREE-001  Exact condition match yields agreed=True.
  AGREE-002  Operator normalization ('>=' matches 'gte') yields agreed=True.
  AGREE-003  Threshold mismatch (50 vs 100) detects disagreement.
  AGREE-004  Operator mismatch ('gte' vs 'gt') detects disagreement.
  AGREE-005  Field mismatch ('activity' vs 'industry') detects disagreement.
  AGREE-006  Obligation type mismatch detects disagreement.
  COMP-001   compile_clause_with_agreement auto-approves when passes agree.
  COMP-002   compile_clause_with_agreement marks PENDING_REVIEW on discrepancy.
  COMP-003   compile_clause_with_agreement marks NON_COMPILABLE on ambiguity.
  COMP-004   compile_clause_with_agreement marks CONDITIONAL_RULE.
  REV-001    submit_review APPROVED transitions status and creates audit log.
  REV-002    submit_review by EXPERT_ADJUDICATOR marks is_gold_rule=True.
  REV-003    submit_review REJECTED transitions status to REJECTED.
  REV-004    submit_review MARKED_NON_COMPILABLE transitions status to NON_COMPILABLE.
  REV-005    submit_review AMENDED updates rule logic.
  REV-006    submit_review rejects invalid reviewer role.
  REV-007    submit_review rejects invalid decision token.
  REV-008    submit_review rejects blank rationale.
  REV-009    submit_review rejects nonexistent rule.
  REV-010    get_pending_reviews filters for PENDING_REVIEW and DRAFT.
  REV-011    get_audit_trail returns chronological audit entries.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.db.repositories import PostgresRegulatoryRepository
from backend.src.engine.review import (
    DECISION_AMENDED,
    DECISION_APPROVED,
    DECISION_MARKED_NON_COMPILABLE,
    DECISION_REJECTED,
    InvalidReviewDecisionError,
    InvalidReviewerRoleError,
    ROLE_EXPERT_ADJUDICATOR,
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_SECONDARY_ANNOTATOR,
    ReviewService,
    RuleNotFoundError,
)
from backend.src.extraction.compiler import (
    CompilationResult,
    MockLLMClient,
    RuleCompiler,
    compute_rule_agreement,
)
from backend.src.models.domain import (
    AppliesIf,
    Condition,
    Obligation,
    Rule,
    Source,
    Validity,
    Verification,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def base_rule() -> Rule:
    """Standard baseline verified rule."""
    quote = (
        "Published on 2024-01-01, commences 2024-06-01. "
        "Regulation 4. Food manufacturers with capacity of 50 kg/day shall label packages."
    )
    return Rule(
        rule_id="RULE-AGREE-001",
        source=Source(
            instrument="Food Act Regulations 2024",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 4",
            page=1,
            quote_span=quote,
        ),
        validity=Validity(published="2024-01-01", commences="2024-06-01"),
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


@pytest.fixture()
def sample_persisted_rule(db_session: Session, base_rule: Rule) -> RuleORM:
    """Seed SourceDocument, Clause, and Rule in SQLite for review testing."""
    # 1. SourceDocument
    doc = SourceDocumentORM(
        id="doc_test_review",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        title="Test Review Regulation",
        authority="Test Authority",
        file_path="backend/data/raw_sources/test.pdf",
        file_size_bytes=1024,
        page_count=1,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add(doc)
    db_session.flush()

    # 2. Clause
    clause = ClauseORM(
        clause_id="clause_rev_01",
        version_number=1,
        document_id="doc_test_review",
        clause_number="4",
        text=base_rule.source.quote_span,
        start_page=1,
        end_page=1,
        char_start=0,
        char_end=len(base_rule.source.quote_span),
    )
    db_session.add(clause)
    db_session.flush()

    # 3. Rule
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(base_rule)
    db_session.flush()

    orm = db_session.get(RuleORM, base_rule.rule_id)
    orm.review_status = "PENDING_REVIEW"
    db_session.commit()
    return orm


# ---------------------------------------------------------------------------
# Semantic Agreement Tests
# ---------------------------------------------------------------------------

def test_agree_001_exact_match(base_rule):
    """Identical rules must produce agreed=True and zero discrepancies."""
    agreed, diffs = compute_rule_agreement(base_rule, base_rule)
    assert agreed is True
    assert diffs == []


def test_agree_002_operator_normalization(base_rule):
    """Normalized operators ('>=' vs 'gte') must match semantically."""
    rule2 = base_rule.model_copy(deep=True)
    rule2.applies_if.all[1].op = ">="  # equivalent to 'gte'

    agreed, diffs = compute_rule_agreement(base_rule, rule2)
    assert agreed is True
    assert diffs == []


def test_agree_003_threshold_mismatch(base_rule):
    """Mismatched threshold values (50 vs 100) must be detected."""
    rule2 = base_rule.model_copy(deep=True)
    rule2.applies_if.all[1].value = 100

    agreed, diffs = compute_rule_agreement(base_rule, rule2)
    assert agreed is False
    assert len(diffs) > 0
    assert "conditions not in" in diffs[0]


def test_agree_004_operator_mismatch(base_rule):
    """Mismatched operators ('gte' vs 'gt') must be detected."""
    rule2 = base_rule.model_copy(deep=True)
    rule2.applies_if.all[1].op = "gt"

    agreed, diffs = compute_rule_agreement(base_rule, rule2)
    assert agreed is False
    assert len(diffs) > 0


def test_agree_005_field_mismatch(base_rule):
    """Different condition fields ('activity' vs 'industry') must be detected."""
    rule2 = base_rule.model_copy(deep=True)
    rule2.applies_if.all[0].field = "industry"

    agreed, diffs = compute_rule_agreement(base_rule, rule2)
    assert agreed is False
    assert len(diffs) > 0


def test_agree_006_obligation_mismatch(base_rule):
    """Mismatched obligation type must be detected."""
    rule2 = base_rule.model_copy(deep=True)
    rule2.obligation.type = "licensing"

    agreed, diffs = compute_rule_agreement(base_rule, rule2)
    assert agreed is False
    assert any("Obligation type mismatch" in d for d in diffs)


# ---------------------------------------------------------------------------
# Compiler Cross-Extraction Tests
# ---------------------------------------------------------------------------

def test_comp_001_compiler_auto_approves_when_agreed(base_rule):
    """Compiler marks review_status='APPROVED' when both passes agree."""
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
    assert result.review_status == "APPROVED"
    assert result.outcome_type == "STANDARD"
    assert result.rule is not None


def test_comp_002_compiler_marks_pending_review_on_discrepancy(base_rule):
    """Compiler marks review_status='PENDING_REVIEW' when passes produce different thresholds."""
    pass_a_dict = base_rule.model_dump()

    pass_b_dict = base_rule.model_dump()
    pass_b_dict["applies_if"]["all"][1]["value"] = 100  # Disagreement!
    pass_b_quote = (
        "Published on 2024-01-01, commences 2024-06-01. "
        "Regulation 4. Food manufacturers with capacity of 100 kg/day shall label packages."
    )
    pass_b_dict["source"]["quote_span"] = pass_b_quote

    raw_text = (
        "Published on 2024-01-01, commences 2024-06-01. "
        "Regulation 4. Food manufacturers with capacity of 50 kg/day shall label packages. "
        "Also capacity of 100 kg/day is mentioned."
    )
    metadata = {
        "instrument": base_rule.source.instrument,
        "authority": base_rule.source.authority,
        "gazette_no": base_rule.source.gazette_no,
        "clause": base_rule.source.clause,
        "page": base_rule.source.page,
    }

    client_a = MockLLMClient(canned_rule_dict=pass_a_dict)
    client_b = MockLLMClient(canned_rule_dict=pass_b_dict)

    compiler = RuleCompiler(llm_client=client_a)
    result = compiler.compile_clause_with_agreement(
        raw_text, metadata, secondary_client=client_b
    )

    assert result.cross_agreement is False
    assert result.review_status == "PENDING_REVIEW"
    assert len(result.discrepancies) > 0


def test_comp_003_compiler_non_compilable():
    """Non-compilable clause produces NON_COMPILABLE status."""
    non_comp_dict = {
        "rule_id": "RULE-NON-COMP",
        "source": {
            "instrument": "Act",
            "authority": "Auth",
            "gazette_no": "1",
            "clause": "1",
            "page": 1,
            "quote_span": "Discretionary powers apply.",
        },
        "validity": {"published": "2024-01-01", "commences": "2024-01-01"},
        "applies_if": {"all": []},
        "obligation": {"type": "standards", "text": "Apply discretion.", "impact_categories": []},
        "verification": {
            "status": "NON_COMPILABLE",
            "extraction_model": "mock",
            "agreement": True,
            "reason": "Statutory discretion cannot be evaluated deterministically.",
        },
    }

    mock_client = MockLLMClient(canned_rule_dict=non_comp_dict)
    compiler = RuleCompiler(llm_client=mock_client)

    result = compiler.compile_clause_with_agreement(
        "Discretionary powers apply.", {"instrument": "Act", "authority": "Auth"}
    )
    assert result.review_status == "NON_COMPILABLE"


def test_comp_004_compiler_conditional_rule(base_rule):
    """Rules flagged as CONDITIONAL_RULE reflect outcome_type='CONDITIONAL_RULE'."""
    rule_dict = base_rule.model_dump()
    rule_dict["verification"]["status"] = "CONDITIONAL_RULE"
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
    assert result.outcome_type == "CONDITIONAL_RULE"


# ---------------------------------------------------------------------------
# Human Review Workflow Tests
# ---------------------------------------------------------------------------

def test_rev_001_submit_review_approved(db_session, sample_persisted_rule):
    """Approving a rule sets review_status='APPROVED' and records audit log."""
    service = ReviewService(db_session)
    updated = service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="annotator_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Verified verbatim quote span and operator gte against clause text.",
    )

    assert updated.review_status == "APPROVED"
    assert updated.is_gold_rule is False

    # Check audit log
    audit_trail = service.get_audit_trail("RULE-AGREE-001")
    assert len(audit_trail) == 1
    assert audit_trail[0].decision == "APPROVED"
    assert audit_trail[0].reviewer_id == "annotator_01"
    assert audit_trail[0].reviewer_role == ROLE_PRIMARY_ANNOTATOR


def test_rev_002_expert_adjudication_designates_gold_rule(db_session, sample_persisted_rule):
    """Approval by EXPERT_ADJUDICATOR marks is_gold_rule=True."""
    service = ReviewService(db_session)
    updated = service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="senior_legal_counsel",
        reviewer_role=ROLE_EXPERT_ADJUDICATOR,
        decision=DECISION_APPROVED,
        rationale="Adjudicated and confirmed by senior legal expert.",
    )

    assert updated.review_status == "APPROVED"
    assert updated.is_gold_rule is True

    gold_rules = service.get_gold_rules()
    assert len(gold_rules) == 1
    assert gold_rules[0].rule_id == "RULE-AGREE-001"


def test_rev_003_submit_review_rejected(db_session, sample_persisted_rule):
    """Rejecting a rule sets review_status='REJECTED'."""
    service = ReviewService(db_session)
    updated = service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="annotator_02",
        reviewer_role=ROLE_SECONDARY_ANNOTATOR,
        decision=DECISION_REJECTED,
        rationale="Numeric threshold hallucinated; text states 500 not 50.",
    )

    assert updated.review_status == "REJECTED"
    assert updated.is_gold_rule is False


def test_rev_004_submit_review_marked_non_compilable(db_session, sample_persisted_rule):
    """Marking non-compilable transitions status to NON_COMPILABLE."""
    service = ReviewService(db_session)
    updated = service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="annotator_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_MARKED_NON_COMPILABLE,
        rationale="Clause depends on undefined ministerial discretion.",
    )

    assert updated.review_status == "NON_COMPILABLE"


def test_rev_005_submit_review_amended(db_session, sample_persisted_rule):
    """Submitting AMENDED updates rule contents and marks approved."""
    service = ReviewService(db_session)
    new_applies_if = {
        "all": [{"field": "production_capacity.kg_per_day", "op": "gte", "value": 75}]
    }

    updated = service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="annotator_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_AMENDED,
        rationale="Amended threshold from 50 to 75 to match corrigendum.",
        amendments={"applies_if": new_applies_if},
    )

    assert updated.review_status == "APPROVED"
    assert updated.applies_if["all"][0]["value"] == 75


def test_rev_006_invalid_reviewer_role(db_session, sample_persisted_rule):
    """Invalid reviewer role raises InvalidReviewerRoleError."""
    service = ReviewService(db_session)
    with pytest.raises(InvalidReviewerRoleError):
        service.submit_review(
            rule_id="RULE-AGREE-001",
            reviewer_id="user_99",
            reviewer_role="UNAUTHORISED_GUEST",
            decision=DECISION_APPROVED,
            rationale="Rationale",
        )


def test_rev_007_invalid_decision_token(db_session, sample_persisted_rule):
    """Invalid decision raises InvalidReviewDecisionError."""
    service = ReviewService(db_session)
    with pytest.raises(InvalidReviewDecisionError):
        service.submit_review(
            rule_id="RULE-AGREE-001",
            reviewer_id="annotator_01",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision="MAYBE_OK",
            rationale="Rationale",
        )


def test_rev_008_empty_rationale_rejected(db_session, sample_persisted_rule):
    """Empty rationale raises ValueError."""
    service = ReviewService(db_session)
    with pytest.raises(ValueError) as exc:
        service.submit_review(
            rule_id="RULE-AGREE-001",
            reviewer_id="annotator_01",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision=DECISION_APPROVED,
            rationale="   ",
        )
    assert "rationale must be provided" in str(exc.value)


def test_rev_009_nonexistent_rule(db_session):
    """Reviewing a nonexistent rule raises RuleNotFoundError."""
    service = ReviewService(db_session)
    with pytest.raises(RuleNotFoundError):
        service.submit_review(
            rule_id="DOES_NOT_EXIST",
            reviewer_id="annotator_01",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision=DECISION_APPROVED,
            rationale="Rationale",
        )


def test_rev_010_get_pending_reviews(db_session, sample_persisted_rule):
    """get_pending_reviews fetches pending rules and ignores approved/rejected."""
    service = ReviewService(db_session)
    pending = service.get_pending_reviews()
    assert len(pending) == 1
    assert pending[0].rule_id == "RULE-AGREE-001"

    # Approve it
    service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="annotator_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Approved",
    )

    pending_after = service.get_pending_reviews()
    assert len(pending_after) == 0


def test_rev_011_get_audit_trail_chronological(db_session, sample_persisted_rule):
    """Audit trail maintains chronological history of decisions."""
    service = ReviewService(db_session)

    # First pass: rejected
    service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="annotator_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_REJECTED,
        rationale="Initial pass rejected: missing unit qualification.",
    )

    # Second pass: amended and approved
    service.submit_review(
        rule_id="RULE-AGREE-001",
        reviewer_id="senior_expert",
        reviewer_role=ROLE_EXPERT_ADJUDICATOR,
        decision=DECISION_AMENDED,
        rationale="Unit clarified; approved for production.",
    )

    trail = service.get_audit_trail("RULE-AGREE-001")
    assert len(trail) == 2
    assert trail[0].decision == "REJECTED"
    assert trail[1].decision == "AMENDED"
    assert trail[1].reviewer_role == ROLE_EXPERT_ADJUDICATOR
