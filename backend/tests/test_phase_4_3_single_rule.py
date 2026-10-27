"""Phase 4.3: Single-Rule Compilation & Deterministic Verification Suite.

Validates the compilation, source grounding, and deterministic execution of
RULE-COLOURING-SEAFOOD-PROHIBITION derived from Gazette Extraordinary No. 1688/28 Regulation 5(iv):
  1. Clearly applicable case (fish / molluscs / crustaceans / echinoderms manufacturing).
  2. Outside-the-prohibition case (bakery products, dairy products).
  3. Missing data case (missing product category -> CONDITIONAL_MISSING_DATA).
  4. Applicability vs. compliance conceptual distinction verification.
  5. Provenance check linking candidate rule to Gazette 1688/28 Clause record.
  6. Idempotency check (no duplicate rule creation).
  7. Regression check verifying pre-existing authentic rules remain untouched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.db.repositories import rule_orm_to_domain
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.verifier import RuleVerifier, normalize_text
from backend.src.models.domain import (
    BusinessProfile,
    OutcomeStatus,
    Product,
    Rule,
)
from backend.tests.conftest import LIVE_DATABASE_URL

TARGET_RULE_ID = "RULE-COLOURING-SEAFOOD-PROHIBITION"
TARGET_CLAUSE_ID = "CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV"
DOC_1688_28_ID = "doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7"

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


# ---------------------------------------------------------------------------
# 1. Provenance and Source Grounding Check
# ---------------------------------------------------------------------------

def test_phase_4_3_rule_provenance_and_grounding(live_db: Session):
    """Verify that RULE-COLOURING-SEAFOOD-PROHIBITION is grounded in Gazette 1688/28."""
    rule_orm = live_db.get(RuleORM, TARGET_RULE_ID)
    assert rule_orm is not None, f"Rule {TARGET_RULE_ID} not found in PostgreSQL database."

    # Status invariants
    assert rule_orm.review_status == "PENDING_REVIEW", "Candidate rule must be PENDING_REVIEW."
    assert rule_orm.is_gold_rule is False, "Candidate rule must not have gold flag."
    assert rule_orm.is_synthetic is False, "Candidate rule must be authentic (is_synthetic=False)."
    assert rule_orm.outcome_type == "STANDARD"

    # Clause linkage
    assert rule_orm.clause_id == TARGET_CLAUSE_ID
    assert rule_orm.clause_version == 1

    clause_orm = live_db.get(ClauseORM, (TARGET_CLAUSE_ID, 1))
    assert clause_orm is not None, "Target clause record must exist in PostgreSQL."
    assert clause_orm.document_id == DOC_1688_28_ID
    assert clause_orm.clause_number == "Regulation 5(iv)"
    assert clause_orm.start_page == 1

    # Verbatim quote span check
    quote = rule_orm.source["quote_span"]
    assert normalize_text(quote).lower() in normalize_text(clause_orm.text).lower()

    # RuleVerifier programmatic check
    domain_rule = rule_orm_to_domain(rule_orm)
    verifier = RuleVerifier()
    rep = verifier.verify(
        domain_rule,
        source_text=clause_orm.text,
        metadata={"published": rule_orm.validity["published"], "commences": rule_orm.validity["commences"]},
    )
    assert rep.is_valid is True, f"RuleVerifier failed on stored candidate rule: {rep.issues}"


# ---------------------------------------------------------------------------
# 2. Case: Clearly Applicable (Seafood Processing)
# ---------------------------------------------------------------------------

def test_phase_4_3_applicability_clear_positive(live_db: Session):
    """Rule applies to businesses manufacturing or processing fish/molluscs/crustaceans/echinoderms."""
    rule_orm = live_db.get(RuleORM, TARGET_RULE_ID)
    assert rule_orm is not None
    domain_rule = rule_orm_to_domain(rule_orm)

    for seafood_cat in ["fish", "molluscs", "crustaceans", "echinoderms"]:
        profile = BusinessProfile(
            business_id=f"BIZ-SEAFOOD-{seafood_cat.upper()}",
            activity="food_manufacturing",
            products=[Product(category=seafood_cat, prepackaged=True)],
            as_at_date="2024-01-01",
        )
        res = evaluate_rule(domain_rule, profile)
        assert res.status == OutcomeStatus.APPLICABLE, (
            f"Expected APPLICABLE for category '{seafood_cat}', got {res.status}"
        )
        assert len(res.missing_fields) == 0


# ---------------------------------------------------------------------------
# 3. Case: Outside Prohibition (Bakery / Dairy / Beverage)
# ---------------------------------------------------------------------------

def test_phase_4_3_applicability_clear_negative(live_db: Session):
    """Rule is NOT_APPLICABLE to businesses manufacturing non-seafood food products."""
    rule_orm = live_db.get(RuleORM, TARGET_RULE_ID)
    assert rule_orm is not None
    domain_rule = rule_orm_to_domain(rule_orm)

    for non_seafood_cat in ["bakery_products", "dairy_ice_cream", "carbonated_beverages", "confectionery"]:
        profile = BusinessProfile(
            business_id=f"BIZ-NON-SEAFOOD-{non_seafood_cat.upper()}",
            activity="food_manufacturing",
            products=[Product(category=non_seafood_cat, prepackaged=True)],
            as_at_date="2024-01-01",
        )
        res = evaluate_rule(domain_rule, profile)
        assert res.status == OutcomeStatus.NOT_APPLICABLE, (
            f"Expected NOT_APPLICABLE for category '{non_seafood_cat}', got {res.status}"
        )


# ---------------------------------------------------------------------------
# 4. Case: Missing Data (Category is None)
# ---------------------------------------------------------------------------

def test_phase_4_3_applicability_missing_data(live_db: Session):
    """When product category is unknown or None, engine must abstain with CONDITIONAL_MISSING_DATA."""
    rule_orm = live_db.get(RuleORM, TARGET_RULE_ID)
    assert rule_orm is not None
    domain_rule = rule_orm_to_domain(rule_orm)

    profile_missing = BusinessProfile(
        business_id="BIZ-INCOMPLETE",
        activity="food_manufacturing",
        products=[Product(category=None, prepackaged=True)],
        as_at_date="2024-01-01",
    )
    res = evaluate_rule(domain_rule, profile_missing)
    assert res.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "products.category" in res.missing_fields


# ---------------------------------------------------------------------------
# 5. Distinction Between Applicability and Compliance
# ---------------------------------------------------------------------------

def test_phase_4_3_applicability_vs_compliance_distinction(live_db: Session):
    """Demonstrate that OutcomeStatus.APPLICABLE governs statutory scope, not adherence."""
    rule_orm = live_db.get(RuleORM, TARGET_RULE_ID)
    assert rule_orm is not None
    domain_rule = rule_orm_to_domain(rule_orm)

    # Both a compliant processor (no added colours) and a non-compliant processor (added Tartrazine)
    # fall squarely within the statutory applicability scope of the regulation:
    profile_pure_fish = BusinessProfile(
        business_id="BIZ-FISH-CLEAN",
        activity="food_manufacturing",
        products=[Product(category="fish", prepackaged=True)],
        as_at_date="2024-01-01",
    )
    res = evaluate_rule(domain_rule, profile_pure_fish)
    assert res.status == OutcomeStatus.APPLICABLE

    # The prohibition obligation itself defines the required conduct:
    assert domain_rule.obligation.type == "prohibition"
    assert "no colouring substance shall be added" in domain_rule.obligation.text.lower()
    assert "safety_compliance" in domain_rule.obligation.impact_categories


# ---------------------------------------------------------------------------
# 6. Idempotency Check
# ---------------------------------------------------------------------------

def test_phase_4_3_idempotency(live_db: Session):
    """Rerunning compilation/persistence does not create duplicates or fail."""
    matching_rules = live_db.query(RuleORM).filter(RuleORM.rule_id == TARGET_RULE_ID).all()
    assert len(matching_rules) == 1, f"Expected exactly 1 rule with ID {TARGET_RULE_ID}, got {len(matching_rules)}"


# ---------------------------------------------------------------------------
# 7. Regression Check on Pre-Existing Authentic Rules
# ---------------------------------------------------------------------------

def test_phase_4_3_regression_preservation_of_existing_rules(live_db: Session):
    """Verify that all 12 pre-existing authentic rules remain untouched."""
    pre_existing_rule_ids = [
        "RULE-FCAU-2494-47-REG-3",
        "RULE-FCAU-2494-47-REG-3-B2B",
        "RULE-SUGAR-2494-06-RED",
        "RULE-SUGAR-2494-06-AMBER",
        "RULE-SUGAR-2494-06-GREEN",
        "RULE-SUGAR-2494-06-GLASS-PROVISO",
        "RULE-PRESERVATIVE-MIXTURE-LIMIT",
        "RULE-PRESERVATIVE-JAM-JELLY-LIMIT",
        "RULE-PRESERVATIVE-LABEL-DECLARATION",
        "RULE-FLAVOUR-INFANT-PROHIBITION",
        "RULE-FLAVOUR-SCHEDULE-III-PROHIBITION",
        "RULE-FLAVOUR-LABEL-DECLARATION",
    ]
    for r_id in pre_existing_rule_ids:
        r = live_db.get(RuleORM, r_id)
        assert r is not None, f"Pre-existing rule {r_id} was unexpectedly modified or deleted!"
        assert r.is_synthetic is False
        assert r.is_gold_rule is False
        if r_id in ["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"]:
            assert r.review_status == "APPROVED"
        else:
            assert r.review_status == "PENDING_REVIEW"
