"""Phase 3.3 Focused Test Suite: Operative Clause Segmentation and Rule Readiness.

Verifies:
  1. Operative clause segmentation across the three verified candidate instruments:
     - 2494-06_E.pdf (Gazette 2494/06 Sugar colour coding amendment)
     - preservative-english.pdf (Gazette 2113/16 Food Preservatives Regulations 2019)
     - food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf (Gazette 1795/51)
  2. Provenance, page references, and exact statutory text grounding.
  3. Exact mathematical constraint preservation (Preservative Regulation 4 percentage sum total).
  4. Exact proviso and threshold preservation (Glass bottle printable space constraint, Sugar thresholds).
  5. Exact statutory prohibition preservation (Flavour enhancers in infant foods and Schedule III).
  6. RuleVerifier validation of all candidate rules into PENDING_REVIEW status.
  7. Clear demarcation between primary annotation and independent expert adjudication (is_gold_rule = False).
  8. Quarantine isolation in hybrid and dense retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from sqlalchemy import text

from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.retrieval import DenseRetrievalEngine, HybridRetrievalEngine
from backend.src.engine.verifier import RuleVerifier, normalize_text
from backend.src.extraction.embedding_client import get_embedding_client
from backend.src.models.domain import (
    AppliesIf,
    Condition,
    Obligation,
    Rule,
    Source,
    Validity,
    Verification,
)
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
        engine = create_engine_from_url(DATABASE_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


POSTGRES_AVAILABLE = _can_connect_to_postgres()

# Document IDs for candidate instruments
DOC_SUGAR = "doc_15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b"
DOC_PRESERVATIVE = "doc_3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f"
DOC_FLAVOURING = "doc_b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a"


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
# 1. Candidate Instruments Clause Inventory & Embeddings
# ---------------------------------------------------------------------------

def test_candidate_instruments_clause_segmentation(live_db):
    """Verify that all 19 operative clauses are segmented with BGE embeddings."""
    sugar_clauses = live_db.query(ClauseORM).filter(ClauseORM.document_id == DOC_SUGAR).all()
    # 5 prior ingestion clauses + 4 newly segmented operative clauses = 9 total
    assert len(sugar_clauses) == 9, f"Expected 9 clauses for Sugar amendment, found {len(sugar_clauses)}"

    preservative_clauses = live_db.query(ClauseORM).filter(ClauseORM.document_id == DOC_PRESERVATIVE).all()
    # 2 prior ingestion clauses + 8 newly segmented operative clauses = 10 total
    assert len(preservative_clauses) == 10, f"Expected 10 clauses for Preservatives, found {len(preservative_clauses)}"

    flavouring_clauses = live_db.query(ClauseORM).filter(ClauseORM.document_id == DOC_FLAVOURING).all()
    # 5 prior ingestion clauses + 7 newly segmented operative clauses = 12 total
    assert len(flavouring_clauses) == 12, f"Expected 12 clauses for Flavourings, found {len(flavouring_clauses)}"

    # Specific 19 newly segmented operative clauses
    new_clause_ids = [
        f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-3-1",
        f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-3-3",
        f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-6-GA",
        f"CLAUSE-{DOC_SUGAR.upper()}-SCHEDULE",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-1",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-2",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-3",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-4",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-5",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-8",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-SCHEDULE-I",
        f"CLAUSE-{DOC_PRESERVATIVE.upper()}-SCHEDULE-II-FRUIT",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-1",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-6",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-7",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-8",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-I",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-II",
        f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-III",
    ]
    assert len(new_clause_ids) == 19

    for cid in new_clause_ids:
        c = live_db.get(ClauseORM, (cid, 1))
        assert c is not None, f"Clause {cid} not found in DB"
        assert c.is_synthetic is False, f"Clause {c.clause_id} must not be synthetic"
        assert c.start_page >= 1, f"Clause {c.clause_id} invalid start_page"
        assert c.end_page >= c.start_page, f"Clause {c.clause_id} invalid end_page"
        assert len(c.text.strip()) > 20, f"Clause {c.clause_id} text is too short"
        assert c.embedding_verified is True, f"Clause {c.clause_id} embedding must be verified"
        assert c.embedding_model == "BAAI/bge-base-en-v1.5"
        assert c.embedding is not None and len(c.embedding) == 768


# ---------------------------------------------------------------------------
# 2. Sugar Amendment Proviso and Exact Threshold Boundaries
# ---------------------------------------------------------------------------

def test_sugar_amendment_proviso_and_thresholds(live_db):
    """Verify glass-bottle printable-space proviso and exact sugar thresholds."""
    # Check glass proviso clause
    proviso_clause = live_db.get(ClauseORM, (f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-3-1", 1))
    assert proviso_clause is not None
    assert "space constraint in the total printable area with respect to glass bottles" in proviso_clause.text
    assert "Column IV" in proviso_clause.text
    assert proviso_clause.start_page == 1
    assert proviso_clause.end_page == 2

    # Check schedule thresholds clause
    sched_clause = live_db.get(ClauseORM, (f"CLAUSE-{DOC_SUGAR.upper()}-SCHEDULE", 1))
    assert sched_clause is not None
    assert "More than 8.0 g/100 ml" in sched_clause.text
    assert "2.5g to 8.0 g/100 ml" in sched_clause.text
    assert "Less than 2.5 g/100 ml" in sched_clause.text

    # Verify candidate rules are PENDING_REVIEW and grounded
    verifier = RuleVerifier()
    rule_ids = [
        "RULE-SUGAR-2494-06-RED",
        "RULE-SUGAR-2494-06-AMBER",
        "RULE-SUGAR-2494-06-GREEN",
        "RULE-SUGAR-2494-06-GLASS-PROVISO",
    ]
    for r_id in rule_ids:
        r_orm = live_db.get(RuleORM, r_id)
        assert r_orm is not None, f"Rule {r_id} not found in database"
        assert r_orm.review_status == "PENDING_REVIEW"
        assert r_orm.is_gold_rule is False
        assert r_orm.is_synthetic is False

        # Run verification check
        c_record = live_db.get(ClauseORM, (r_orm.clause_id, 1))
        rep = verifier.verify(
            Rule(
                rule_id=r_orm.rule_id,
                source=Source(**r_orm.source),
                validity=Validity(**r_orm.validity),
                applies_if=AppliesIf(all=[Condition(**c) for c in r_orm.applies_if["all"]]),
                exceptions=[Condition(**e) for e in r_orm.exceptions] if r_orm.exceptions else None,
                obligation=Obligation(
                    type=r_orm.obligation["type"],
                    text=r_orm.obligation["description"],
                    impact_categories=r_orm.obligation["impact_categories"],
                ),
                verification=Verification(status="pending_review", extraction_model="test", agreement=False),
            ),
            source_text=c_record.text,
            metadata={"published": r_orm.validity["published"], "commences": r_orm.validity["commences"]},
        )
        assert rep.is_valid is True, f"Rule {r_id} failed verification: {rep.issues}"


# ---------------------------------------------------------------------------
# 3. Preservative Regulations Summation Formula & Item Limits
# ---------------------------------------------------------------------------

def test_preservatives_summation_formula_and_fruit_limits(live_db):
    """Verify exact summation percentage formula and food-specific maximum limits."""
    # Check Regulation 4 mixture formula
    reg4 = live_db.get(ClauseORM, (f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-4", 1))
    assert reg4 is not None
    assert "sum total of the preservatives does not exceed one hundred percentage" in reg4.text
    assert "expressed as a percentage of the maximum quantity" in reg4.text

    # Check Schedule II fruit limits
    fruit_sched = live_db.get(ClauseORM, (f"CLAUSE-{DOC_PRESERVATIVE.upper()}-SCHEDULE-II-FRUIT", 1))
    assert fruit_sched is not None
    assert "Jams, Jellies, marmalades: Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP" in fruit_sched.text

    # Verify candidate rules
    verifier = RuleVerifier()
    rule_ids = [
        "RULE-PRESERVATIVE-MIXTURE-LIMIT",
        "RULE-PRESERVATIVE-JAM-JELLY-LIMIT",
        "RULE-PRESERVATIVE-LABEL-DECLARATION",
    ]
    for r_id in rule_ids:
        r_orm = live_db.get(RuleORM, r_id)
        assert r_orm is not None, f"Rule {r_id} not found in database"
        assert r_orm.review_status == "PENDING_REVIEW"
        assert r_orm.is_gold_rule is False

        c_record = live_db.get(ClauseORM, (r_orm.clause_id, 1))
        rep = verifier.verify(
            Rule(
                rule_id=r_orm.rule_id,
                source=Source(**r_orm.source),
                validity=Validity(**r_orm.validity),
                applies_if=AppliesIf(all=[Condition(**c) for c in r_orm.applies_if["all"]]),
                exceptions=[Condition(**e) for e in r_orm.exceptions] if r_orm.exceptions else None,
                obligation=Obligation(
                    type=r_orm.obligation["type"],
                    text=r_orm.obligation["description"],
                    impact_categories=r_orm.obligation["impact_categories"],
                ),
                verification=Verification(status="pending_review", extraction_model="test", agreement=False),
            ),
            source_text=c_record.text,
            metadata={"published": r_orm.validity["published"], "commences": r_orm.validity["commences"]},
        )
        assert rep.is_valid is True, f"Rule {r_id} failed verification: {rep.issues}"


# ---------------------------------------------------------------------------
# 4. Flavourings Regulations Prohibitions & Labelling
# ---------------------------------------------------------------------------

def test_flavourings_infant_and_schedule_iii_prohibitions(live_db):
    """Verify prohibitions on flavour enhancers in infant foods and Schedule III categories."""
    reg7 = live_db.get(ClauseORM, (f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-7", 1))
    assert reg7 is not None
    assert "shall not be added to any food for infants or young children below three years of age" in reg7.text
    assert "shall not be used in the foods specified in Schedule III hereto" in reg7.text

    sched3 = live_db.get(ClauseORM, (f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-III", 1))
    assert sched3 is not None
    assert "16. Bakery Products" in sched3.text
    assert "1. Milk and Milk Products" in sched3.text

    verifier = RuleVerifier()
    rule_ids = [
        "RULE-FLAVOUR-INFANT-PROHIBITION",
        "RULE-FLAVOUR-SCHEDULE-III-PROHIBITION",
        "RULE-FLAVOUR-LABEL-DECLARATION",
    ]
    for r_id in rule_ids:
        r_orm = live_db.get(RuleORM, r_id)
        assert r_orm is not None, f"Rule {r_id} not found in database"
        assert r_orm.review_status == "PENDING_REVIEW"
        assert r_orm.is_gold_rule is False

        c_record = live_db.get(ClauseORM, (r_orm.clause_id, 1))
        rep = verifier.verify(
            Rule(
                rule_id=r_orm.rule_id,
                source=Source(**r_orm.source),
                validity=Validity(**r_orm.validity),
                applies_if=AppliesIf(all=[Condition(**c) for c in r_orm.applies_if["all"]]),
                exceptions=[Condition(**e) for e in r_orm.exceptions] if r_orm.exceptions else None,
                obligation=Obligation(
                    type=r_orm.obligation["type"],
                    text=r_orm.obligation["description"],
                    impact_categories=r_orm.obligation["impact_categories"],
                ),
                verification=Verification(status="pending_review", extraction_model="test", agreement=False),
            ),
            source_text=c_record.text,
            metadata={"published": r_orm.validity["published"], "commences": r_orm.validity["commences"]},
        )
        assert rep.is_valid is True, f"Rule {r_id} failed verification: {rep.issues}"


# ---------------------------------------------------------------------------
# 5. Adjudication & Gold Status Integrity
# ---------------------------------------------------------------------------

def test_expert_adjudication_and_gold_status_integrity(live_db):
    """Ensure no unadjudicated rule is marked as gold or expert-approved."""
    # All candidate rules must be PENDING_REVIEW and is_gold_rule=False
    candidate_rules = live_db.query(RuleORM).filter(RuleORM.review_status == "PENDING_REVIEW").all()
    # Exactly 11 candidate rules (10 from Phase 3.3 segmentation + 1 from Phase 4.3 RULE-COLOURING-SEAFOOD-PROHIBITION)
    assert len(candidate_rules) == 11, f"Expected 11 candidate rules, found {len(candidate_rules)}"
    for r in candidate_rules:
        assert r.is_gold_rule is False
        assert r.is_synthetic is False

    # Authentic rules in DB must be is_gold_rule=False
    authentic_approved = live_db.query(RuleORM).filter(
        RuleORM.review_status == "APPROVED",
        RuleORM.is_synthetic == False
    ).all()
    assert len(authentic_approved) == 2
    for r in authentic_approved:
        assert r.is_gold_rule is False
        # Review audit must show PRIMARY_ANNOTATOR, not EXPERT_ADJUDICATOR
        audit = live_db.query(HumanReviewAuditORM).filter(HumanReviewAuditORM.rule_id == r.rule_id).first()
        assert audit is not None
        assert audit.reviewer_role == "PRIMARY_ANNOTATOR"


# ---------------------------------------------------------------------------
# 6. Retrieval Isolation & Hygiene
# ---------------------------------------------------------------------------

def test_retrieval_isolation_of_quarantined_records(live_db):
    """Ensure retrieval engines cannot surface quarantined draft or synthetic documents."""
    emb_client = get_embedding_client(provider="sentence-transformers", allow_mock_fallback=False)
    dense_engine = DenseRetrievalEngine(db=live_db, embedding_client=emb_client)
    hybrid_engine = HybridRetrievalEngine(db=live_db, dense_engine=dense_engine)

    results = hybrid_engine.search(
        query="business to business food labelling exemption mandatory requirements",
        top_k=5,
    )
    assert len(results) > 0
    for res in results:
        # Check clause record in DB
        clause = live_db.get(ClauseORM, (res.clause_id, 1))
        assert clause is not None
        assert clause.is_synthetic is False, f"Quarantined synthetic clause {res.clause_id} retrieved"
        assert clause.document_id != "doc_labelling_regulations_final_2026", "Quarantined draft retrieved"
        assert clause.document_id != "doc_cea_epl_2022", "Quarantined mock CEA document retrieved"
        assert clause.document_id != "doc_lec_03", "Quarantined mock document retrieved"
