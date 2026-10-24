"""Milestone: Authoritative Gazette and Legal-Semantics Repair Test Suite.

Verifies and demonstrates an end-to-end, auditable pipeline using the officially
promulgated Sri Lankan regulatory source:
  - Promulgated Source: Sri Lanka Gazette Extraordinary No. 2494/47 (2026-06-26)
  - Raw PDF Path: backend/data/raw_sources/2494-47_E.pdf
  - Reproducible SHA-256: 83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054
  - Official Government URL: http://www.documents.gov.lk/files/egz/2026/6/2494-47_E.pdf
  - Target Regulation: Regulation 3 (General retail mandate + Proviso (b) B2B affirmative requirements)
  - Coordinates: Spans Page 1 [826, 1074] and Page 2 [199, 1226]
  - Normalization: Handles Gazette typographic ligatures (PUA characters U+E055, U+E056, etc.)
  - Distinction: Promulgated Gazette vs. Earlier Committee Draft (Labelling_Regulations_Final_-_11.02.2026.pdf)
  - Review Integrity: Candidate (PENDING_REVIEW) -> Verified (RuleVerifier) -> Human Reviewed (PRIMARY_ANNOTATOR, is_gold_rule=False)
  - Legal Semantics: Retail packaged food rule vs. B2B affirmative 10 disclosures + "Not for retail sale" marking
"""

import datetime
import hashlib
from pathlib import Path
import pytest
import pymupdf
from fastapi.testclient import TestClient

from backend.data.seed_real_slice import seed_real_slice
from backend.src.db.models import (
    Base,
    ClauseORM,
    DocumentPageORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
)
from backend.src.db.repositories import (
    PostgresRegulatoryRepository,
    rule_domain_to_orm_dict,
    rule_orm_to_domain,
)
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.impact_mapper import map_impact
from backend.src.engine.review import (
    DECISION_APPROVED,
    DECISION_AMENDED,
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_EXPERT_ADJUDICATOR,
    ReviewService,
)
from backend.src.main import app, get_db
from backend.src.engine.review import (
    DECISION_APPROVED,
    DECISION_AMENDED,
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_EXPERT_ADJUDICATOR,
    ReviewService,
)
from backend.src.engine.verifier import RuleVerifier, normalize_text
from backend.src.models.domain import (
    AppliesIf,
    BusinessProfile,
    Condition,
    Obligation,
    OutcomeStatus,
    Product,
    Rule,
    Source,
    Validity,
    Verification,
)

# ---------------------------------------------------------------------------
# Constants for Promulgated Sri Lankan Gazette Extraordinary No. 2494/47
# ---------------------------------------------------------------------------
GAZETTE_PDF_PATH = Path("backend/data/raw_sources/2494-47_E.pdf")
EXPECTED_GAZETTE_SHA256 = "83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054"
EXPECTED_GAZETTE_PAGES = 25
GAZETTE_OFFICIAL_URL = "http://www.documents.gov.lk/files/egz/2026/6/2494-47_E.pdf"

GAZETTE_DOC_ID = "doc_gazette_2494_47"
GAZETTE_DOC_TITLE = "Sri Lanka Gazette Extraordinary No. 2494/47: Food (Labelling and Advertising) Regulations 2026"
GAZETTE_AUTHORITY = "Minister of Health and Mass Media / Food Advisory Committee"
GAZETTE_NO = "Gazette Extraordinary No. 2494/47"

CLAUSE_ID = "CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3"
CLAUSE_NUMBER = "Regulation 3"

COMMENCEMENT_DATE = "2026-07-01"
PUBLICATION_DATE = "2026-06-26"

VERBATIM_RETAIL_QUOTE = (
    "A person shall not import, transport, distribute, store, sell, offer for sale, expose or keep for sale "
    "or advertise, any food contained in a package or container, unless such package or container is "
    "labelled in accordance with these regulations:"
)

VERBATIM_B2B_QUOTE = (
    "business-to-business food products that are exempted from other labelling requirements in these regulations "
    "except the following mandatory labelling requirements- (i) common name (in either of the three languages); "
    "(ii) trade name (if applicable); (iii) net contents; (iv) date of manufacture; (v) date of expiry; "
    "(vi) batch number; (vii) manufacturer's name and address; (viii) distributor's name and address; "
    "(ix) country of origin in case of imported foods; and (x) a complete list of ingredients. "
    "Provided further that the statement \"Not for retail sale\" shall be printed on the label or affixed "
    "through a supplementary label of such business-to-business food products clearly and conspicuously in "
    "bold type and font size of not less than three millimetres (3 mm)."
)

# Earlier Committee Draft constants for distinction testing
DRAFT_PDF_PATH = Path("backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
EXPECTED_DRAFT_SHA256 = "c70b5668131b76ff206897ef391cb3402bb4bf6be39a76ad1400d24c07330142"
EXPECTED_DRAFT_PAGES = 22


@pytest.fixture
def test_db():
    """In-memory SQLite database session factory for isolated testing."""
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def seeded_real_db(test_db):
    """Provides an isolated database already seeded with the authoritative real Gazette slice."""
    seed_real_slice(session=test_db)
    return test_db


@pytest.fixture
def client_with_real_slice(seeded_real_db):
    """FastAPI TestClient with get_db overridden to use seeded_real_db."""
    def _override_get_db():
        try:
            yield seeded_real_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ===========================================================================
# 1. Authoritative Provenance and Hash Verification
# ===========================================================================

def test_promulgated_gazette_provenance_and_hash():
    """Task 1.1-1.3: Verify published Gazette PDF existence, hash, size, and government metadata."""
    assert GAZETTE_PDF_PATH.exists(), f"Published Gazette PDF missing at {GAZETTE_PDF_PATH}"

    file_bytes = GAZETTE_PDF_PATH.read_bytes()
    computed_hash = hashlib.sha256(file_bytes).hexdigest()
    assert computed_hash == EXPECTED_GAZETTE_SHA256, (
        f"Hash mismatch! Expected {EXPECTED_GAZETTE_SHA256}, got {computed_hash}"
    )
    assert len(file_bytes) == 424172

    doc = pymupdf.open(str(GAZETTE_PDF_PATH))
    assert len(doc) == EXPECTED_GAZETTE_PAGES

    # Verify Page 1 contains the official statutory masthead and government download URL
    p1_text = doc[0].get_text()
    assert "FOOD ACT, No. 26 OF 1980" in p1_text
    assert "This Gazette Extraordinary can be downloaded from www.documents.gov.lk" in p1_text
    assert "Dr. Nalinda Jayatissa" in p1_text
    assert "Minister of Health and Mass Media" in p1_text
    assert "26th June, 2026" in p1_text
    assert "No. 2494/47 - FRIDAY, JUNE 26, 2026" in p1_text

    # Verify Regulation 1 commencement date and Regulation 2 transitional exemption
    assert "Food (Labelling and Advertising) Regulations 2026 and shall come into operation\non 01st July 2026" in p1_text
    assert "2.\nThese regulations shall not apply to food products manufactured prior to the date of coming into operation" in p1_text
    doc.close()


def test_distinction_between_promulgated_gazette_and_draft():
    """Task 1.6-1.7: Explicitly distinguish published Gazette from the earlier committee draft."""
    assert DRAFT_PDF_PATH.exists(), f"Committee draft missing at {DRAFT_PDF_PATH}"

    draft_bytes = DRAFT_PDF_PATH.read_bytes()
    draft_hash = hashlib.sha256(draft_bytes).hexdigest()
    assert draft_hash == EXPECTED_DRAFT_SHA256

    # Distinct SHA-256 hashes and page counts
    assert EXPECTED_GAZETTE_SHA256 != EXPECTED_DRAFT_SHA256
    assert EXPECTED_GAZETTE_PAGES == 25
    assert EXPECTED_DRAFT_PAGES == 22

    # Verify regulation numbering differs between draft and promulgated Gazette
    doc_gazette = pymupdf.open(str(GAZETTE_PDF_PATH))
    p1_gazette = doc_gazette[0].get_text()
    doc_gazette.close()

    doc_draft = pymupdf.open(str(DRAFT_PDF_PATH))
    p1_draft = doc_draft[0].get_text()
    doc_draft.close()

    # In Gazette 2494/47: General labelling prohibition is Regulation 3
    assert "3.\nA person shall not import, transport, distribute, store, sell" in p1_gazette
    # In Draft: General labelling prohibition was numbered Regulation 2
    assert "2. A person shall not import, transport, distribute, store, sell" in p1_draft


# ===========================================================================
# 2. Clause Grounding and Ligature Normalization
# ===========================================================================

def test_gazette_clause_grounding_and_ligature_normalization():
    """Task 1.4-1.5: Verify exact coordinates and PUA typographic ligature normalization."""
    doc = pymupdf.open(str(GAZETTE_PDF_PATH))
    p1_text = doc[0].get_text()
    p2_text = doc[1].get_text()
    doc.close()

    # Regulation 3 starts on Page 1 at offset 826
    r3_p1_idx = p1_text.find("3.\n")
    assert r3_p1_idx == 826

    # In raw Gazette text, "offer" contains typographic PUA ligature U+E055
    assert "o\ue055er for sale" in p1_text

    # In raw Gazette text on Page 2, "affixed" contains typographic PUA ligature U+E056
    assert "a\ue056xed through" in p2_text

    # Verify normalize_text in verifier handles these ligatures cleanly
    norm_p1 = normalize_text(p1_text)
    norm_p2 = normalize_text(p2_text)

    # Normalized text contains standard ASCII ligatures
    assert "offer for sale" in norm_p1
    assert "affixed through" in norm_p2

    # Verify RuleVerifier grounds normalized quote spans against the Gazette pages
    verifier = RuleVerifier()
    rule_retail = Rule(
        rule_id="RULE-FCAU-2494-47-REG-3",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause=CLAUSE_NUMBER,
            page=1,
            quote_span=VERBATIM_RETAIL_QUOTE,
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(all=[Condition(field="products.prepackaged", op="eq", value=True)]),
        obligation=Obligation(type="labelling", text="General labelling mandate", impact_categories=["labelling"]),
        verification=Verification(status="PENDING_REVIEW", extraction_model="test", agreement=True),
    )
    v_report_retail = verifier.verify(rule_retail, source_text=p1_text)
    assert v_report_retail.is_valid is True
    assert v_report_retail.status == "verified"

    rule_b2b = Rule(
        rule_id="RULE-FCAU-2494-47-REG-3-B2B",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause="Regulation 3 Proviso (b)",
            page=2,
            quote_span=VERBATIM_B2B_QUOTE,
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(all=[Condition(field="market.b2b_only", op="eq", value=True)]),
        obligation=Obligation(
            type="labelling",
            text="B2B labelling and 'Not for retail sale' mark",
            impact_categories=["labelling"],
        ),
        verification=Verification(status="PENDING_REVIEW", extraction_model="test", agreement=True),
    )
    v_report_b2b = verifier.verify(rule_b2b, source_text=f"{p1_text}\n{p2_text}")
    assert v_report_b2b.is_valid is True
    assert v_report_b2b.status == "verified"


# ===========================================================================
# 3. Rule AST Compilation and B2B Representation
# ===========================================================================

def test_typed_rules_preserve_statutory_structure():
    """Task 2: AST preserves Retail rule and affirmative B2B obligations from Regulation 3."""
    # Retail rule
    retail_rule = Rule(
        rule_id="RULE-FCAU-2494-47-REG-3",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause=CLAUSE_NUMBER,
            page=1,
            quote_span=VERBATIM_RETAIL_QUOTE,
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(
            all=[
                Condition(
                    field="activity",
                    op="in",
                    value=["food_manufacturing", "catering", "retail_trade", "distribution", "import", "storage"],
                ),
                Condition(field="products.prepackaged", op="eq", value=True),
            ]
        ),
        exceptions=[
            Condition(field="packaged_in_presence_of_purchaser", op="eq", value=True),
            Condition(field="market.b2b_only", op="eq", value=True),
        ],
        obligation=Obligation(
            type="labelling",
            text="Food contained in a package or container must be labelled in accordance with the Food (Labelling and Advertising) Regulations 2026.",
            impact_categories=["labelling", "packaging", "retail_distribution"],
        ),
        verification=Verification(status="PENDING_REVIEW", extraction_model="manual_audit", agreement=True),
    )
    assert retail_rule.validity.commences == "2026-07-01"
    assert len(retail_rule.exceptions) == 2

    # B2B affirmative rule
    b2b_rule = Rule(
        rule_id="RULE-FCAU-2494-47-REG-3-B2B",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause="Regulation 3 Proviso (b)",
            page=2,
            quote_span=VERBATIM_B2B_QUOTE,
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="in", value=["food_manufacturing", "distribution", "import", "storage"]),
                Condition(field="products.prepackaged", op="eq", value=True),
                Condition(field="market.b2b_only", op="eq", value=True),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="labelling",
            text="Business-to-business food products must display 10 mandatory disclosures and 'Not for retail sale' mark.",
            impact_categories=["labelling", "packaging", "b2b_compliance"],
            disclosures=[
                "common_name",
                "trade_name",
                "net_contents",
                "date_of_manufacture",
                "date_of_expiry",
                "batch_number",
                "manufacturer_details",
                "distributor_details",
                "country_of_origin",
                "ingredients_list",
                "not_for_retail_sale_statement",
            ],
        ),
        verification=Verification(status="PENDING_REVIEW", extraction_model="manual_audit", agreement=True),
    )
    assert len(b2b_rule.obligation.disclosures) == 11
    assert "not_for_retail_sale_statement" in b2b_rule.obligation.disclosures
    assert "common_name" in b2b_rule.obligation.disclosures


# ===========================================================================
# 4. Review Integrity and State Machine Transitions
# ===========================================================================

def test_provenance_lifecycle_distinction_with_db(test_db):
    """Task 3: Enforce strict distinction between candidate, verified, researcher review, and gold expert adjudication."""
    doc_orm = SourceDocumentORM(
        id=GAZETTE_DOC_ID,
        title=GAZETTE_DOC_TITLE,
        authority=GAZETTE_AUTHORITY,
        instrument_type="gazette_regulation",
        gazette_no=GAZETTE_NO,
        source_url=GAZETTE_OFFICIAL_URL,
        file_path=str(GAZETTE_PDF_PATH),
        file_size_bytes=len(GAZETTE_PDF_PATH.read_bytes()),
        sha256_hash=EXPECTED_GAZETTE_SHA256,
        page_count=EXPECTED_GAZETTE_PAGES,
        extraction_status="SUCCESS",
        extraction_tool="pymupdf",
        publication_date=datetime.date(2026, 6, 26),
    )
    clause_orm = ClauseORM(
        clause_id=CLAUSE_ID,
        version_number=1,
        document_id=GAZETTE_DOC_ID,
        clause_number=CLAUSE_NUMBER,
        text=f"{VERBATIM_RETAIL_QUOTE}\n\n{VERBATIM_B2B_QUOTE}",
        start_page=1,
        end_page=2,
        char_start=826,
        char_end=1226,
        is_compilable=True,
    )
    test_db.add(doc_orm)
    test_db.commit()
    test_db.add(clause_orm)
    test_db.commit()

    candidate_orm = RuleORM(
        rule_id="RULE-FCAU-2494-47-REG-3",
        clause_id=CLAUSE_ID,
        clause_version=1,
        outcome_type="STANDARD",
        applies_if={"all": [{"field": "products.prepackaged", "op": "eq", "value": True}]},
        exceptions=[{"field": "market.b2b_only", "op": "eq", "value": True}],
        obligation={"type": "labelling", "text": "Retail labelling", "impact_categories": ["labelling"]},
        validity={"published": PUBLICATION_DATE, "commences": COMMENCEMENT_DATE},
        source={"clause": CLAUSE_NUMBER, "instrument": GAZETTE_DOC_TITLE, "authority": GAZETTE_AUTHORITY, "gazette_no": GAZETTE_NO, "page": 1, "quote_span": VERBATIM_RETAIL_QUOTE},
        review_status="PENDING_REVIEW",
        is_gold_rule=False,
    )
    test_db.add(candidate_orm)
    test_db.commit()

    # Stage 1: Candidate is unreviewed
    persisted = test_db.get(RuleORM, "RULE-FCAU-2494-47-REG-3")
    assert persisted.review_status == "PENDING_REVIEW"
    assert persisted.is_gold_rule is False
    assert len(persisted.audit_log) == 0

    # Stage 2: Technical verification DOES NOT alter legal review status
    verifier = RuleVerifier()
    doc = pymupdf.open(str(GAZETTE_PDF_PATH))
    p1_text = doc[0].get_text()
    doc.close()
    v_report = verifier.verify(
        Rule(
            rule_id=persisted.rule_id,
            source=Source(**persisted.source),
            validity=Validity(**persisted.validity),
            applies_if=AppliesIf(**persisted.applies_if),
            exceptions=persisted.exceptions,
            obligation=Obligation(**persisted.obligation),
            verification=Verification(status="PENDING_REVIEW", extraction_model="test", agreement=True),
        ),
        source_text=p1_text,
    )
    assert v_report.is_valid is True
    assert persisted.review_status == "PENDING_REVIEW"  # Unchanged!

    # Stage 3: Researcher review approves rule, but is_gold_rule remains False
    review_svc = ReviewService(test_db)
    review_svc.submit_review(
        rule_id="RULE-FCAU-2494-47-REG-3",
        reviewer_id="researcher_engineer_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale="Verified against published Gazette 2494/47 Regulation 3. External legal adjudication pending.",
    )
    test_db.refresh(persisted)
    assert persisted.review_status == "APPROVED"
    assert persisted.is_gold_rule is False  # Primary annotator review is NOT gold!
    assert len(persisted.audit_log) == 1
    assert persisted.audit_log[0].reviewer_role == ROLE_PRIMARY_ANNOTATOR

    # Stage 4: Only EXPERT_ADJUDICATOR role can designate is_gold_rule = True
    review_svc.submit_review(
        rule_id="RULE-FCAU-2494-47-REG-3",
        reviewer_id="attorney_food_law_01",
        reviewer_role=ROLE_EXPERT_ADJUDICATOR,
        decision=DECISION_APPROVED,
        rationale="Adjudicated by qualified regulatory counsel as legally accurate gold rule.",
    )
    test_db.refresh(persisted)
    assert persisted.is_gold_rule is True
    assert len(persisted.audit_log) == 2


# ===========================================================================
# 5. Deterministic Evaluation on Real Legal Conditions
# ===========================================================================

@pytest.fixture
def gazette_rules():
    """Return both Regulation 3 Retail and B2B rule objects."""
    retail = Rule(
        rule_id="RULE-FCAU-2494-47-REG-3",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause=CLAUSE_NUMBER,
            page=1,
            quote_span=VERBATIM_RETAIL_QUOTE,
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="in", value=["food_manufacturing", "catering", "retail_trade"]),
                Condition(field="products.prepackaged", op="eq", value=True),
            ]
        ),
        exceptions=[
            Condition(field="packaged_in_presence_of_purchaser", op="eq", value=True),
            Condition(field="market.b2b_only", op="eq", value=True),
        ],
        obligation=Obligation(type="labelling", text="General retail labelling mandate", impact_categories=["labelling"]),
        verification=Verification(status="APPROVED", extraction_model="manual_audit", agreement=True),
    )
    b2b = Rule(
        rule_id="RULE-FCAU-2494-47-REG-3-B2B",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause="Regulation 3 Proviso (b)",
            page=2,
            quote_span=VERBATIM_B2B_QUOTE,
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="in", value=["food_manufacturing", "catering", "retail_trade"]),
                Condition(field="products.prepackaged", op="eq", value=True),
                Condition(field="market.b2b_only", op="eq", value=True),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="labelling",
            text="B2B 10 disclosures and 'Not for retail sale' mark",
            impact_categories=["labelling", "b2b_compliance"],
            disclosures=[
                "common_name", "trade_name", "net_contents", "date_of_manufacture",
                "date_of_expiry", "batch_number", "manufacturer_details",
                "distributor_details", "country_of_origin", "ingredients_list",
                "not_for_retail_sale_statement",
            ],
        ),
        verification=Verification(status="APPROVED", extraction_model="manual_audit", agreement=True),
    )
    return retail, b2b


def test_deterministic_evaluation_retail_case(gazette_rules):
    """Task 4.3: Packaged food producer post-commencement -> Retail APPLICABLE, B2B NOT_APPLICABLE."""
    retail_rule, b2b_rule = gazette_rules
    profile = BusinessProfile(
        business_id="BIZ-GAZETTE-001",
        activity="food_manufacturing",
        products=[Product(category="spices", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": False},
    )
    res_retail = evaluate_rule(rule=retail_rule, profile=profile, as_at_date="2026-07-15")
    assert res_retail.status == OutcomeStatus.APPLICABLE
    assert res_retail.missing_fields == []

    res_b2b = evaluate_rule(rule=b2b_rule, profile=profile, as_at_date="2026-07-15")
    assert res_b2b.status == OutcomeStatus.NOT_APPLICABLE


def test_deterministic_evaluation_purchaser_presence_exception(gazette_rules):
    """Task 4.4: Packaging in presence of purchaser -> NOT_APPLICABLE under both rules."""
    retail_rule, b2b_rule = gazette_rules
    profile = BusinessProfile(
        business_id="BIZ-GAZETTE-002",
        activity="retail_trade",
        products=[Product(category="grains", prepackaged=True)],
        packaged_in_presence_of_purchaser=True,
        market={"b2b_only": False},
    )
    res_retail = evaluate_rule(rule=retail_rule, profile=profile, as_at_date="2026-07-15")
    assert res_retail.status == OutcomeStatus.NOT_APPLICABLE
    assert "exception condition met" in res_retail.reason.lower()

    res_b2b = evaluate_rule(rule=b2b_rule, profile=profile, as_at_date="2026-07-15")
    assert res_b2b.status == OutcomeStatus.NOT_APPLICABLE


def test_deterministic_evaluation_b2b_affirmative_case(gazette_rules):
    """Task 4.5: B2B manufacturer exempt from retail labelling, but APPLICABLE for B2B requirements."""
    retail_rule, b2b_rule = gazette_rules
    profile = BusinessProfile(
        business_id="BIZ-GAZETTE-003",
        activity="food_manufacturing",
        products=[Product(category="bulk_tea", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": True},
    )
    # Retail rule: exempt
    res_retail = evaluate_rule(rule=retail_rule, profile=profile, as_at_date="2026-07-15")
    assert res_retail.status == OutcomeStatus.NOT_APPLICABLE
    assert "exception condition met" in res_retail.reason.lower()

    # B2B rule: affirmative obligations apply!
    res_b2b = evaluate_rule(rule=b2b_rule, profile=profile, as_at_date="2026-07-15")
    assert res_b2b.status == OutcomeStatus.APPLICABLE
    assert res_b2b.missing_fields == []
    assert len(b2b_rule.obligation.disclosures) == 11


def test_deterministic_evaluation_missing_data_prepackaged(gazette_rules):
    """Task 4.6: Unknown prepackaged status produces CONDITIONAL_MISSING_DATA."""
    retail_rule, b2b_rule = gazette_rules
    profile = BusinessProfile(
        business_id="BIZ-GAZETTE-004",
        activity="food_manufacturing",
        products=[Product(category="bakery", prepackaged=None)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": False},
    )
    # Retail rule: prepackaged=None is decisive -> CONDITIONAL_MISSING_DATA
    res_retail = evaluate_rule(rule=retail_rule, profile=profile, as_at_date="2026-07-15")
    assert res_retail.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "products.prepackaged" in res_retail.missing_fields

    # B2B rule: when market is b2b_only=True, prepackaged=None is decisive -> CONDITIONAL_MISSING_DATA
    profile_b2b = BusinessProfile(
        business_id="BIZ-GAZETTE-004-B2B",
        activity="food_manufacturing",
        products=[Product(category="bakery", prepackaged=None)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": True},
    )
    res_b2b = evaluate_rule(rule=b2b_rule, profile=profile_b2b, as_at_date="2026-07-15")
    assert res_b2b.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "products.prepackaged" in res_b2b.missing_fields


def test_deterministic_evaluation_missing_data_market_channel(gazette_rules):
    """Task 4.6: Unknown market channel produces CONDITIONAL_MISSING_DATA on both branches."""
    retail_rule, b2b_rule = gazette_rules
    profile = BusinessProfile(
        business_id="BIZ-GAZETTE-005",
        activity="food_manufacturing",
        products=[Product(category="bakery", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market=None,  # Market channel unknown
    )
    res_retail = evaluate_rule(rule=retail_rule, profile=profile, as_at_date="2026-07-15")
    assert res_retail.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "market.b2b_only" in res_retail.missing_fields

    res_b2b = evaluate_rule(rule=b2b_rule, profile=profile, as_at_date="2026-07-15")
    assert res_b2b.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "market.b2b_only" in res_b2b.missing_fields


def test_deterministic_evaluation_temporal_prior_to_commencement(gazette_rules):
    """Evaluation prior to July 01, 2026 commencement -> NOT_APPLICABLE (NOT_YET_IN_FORCE)."""
    retail_rule, _ = gazette_rules
    profile = BusinessProfile(
        business_id="BIZ-GAZETTE-006",
        activity="food_manufacturing",
        products=[Product(category="spices", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": False},
    )
    res = evaluate_rule(rule=retail_rule, profile=profile, as_at_date="2026-05-01")
    assert res.status == OutcomeStatus.NOT_APPLICABLE
    assert res.temporal_status == "NOT_YET_IN_FORCE"


def test_deterministic_evaluation_conditional_rule():
    """Rule with outcome_type='CONDITIONAL_RULE' -> CONDITIONAL_RULE outcome."""
    cond_rule = Rule(
        rule_id="RULE-FCAU-2494-47-COND",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause="Regulation 4(4)",
            page=2,
            quote_span="The importer shall maintain documentary evidence",
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(all=[Condition(field="activity", op="eq", value="import")]),
        obligation=Obligation(type="compliance", text="Maintain documentary evidence", impact_categories=["import"]),
        verification=Verification(status="CONDITIONAL_RULE", extraction_model="test", agreement=True),
    )
    profile = BusinessProfile(business_id="BIZ-GAZETTE-007", activity="import")
    res = evaluate_rule(rule=cond_rule, profile=profile, as_at_date="2026-07-15")
    assert res.status == OutcomeStatus.CONDITIONAL_RULE


def test_deterministic_evaluation_unsupported_clause():
    """Clause marked NON_COMPILABLE -> UNSUPPORTED outcome."""
    unsupp_rule = Rule(
        rule_id="RULE-FCAU-2494-47-UNSUPP",
        source=Source(
            instrument=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            gazette_no=GAZETTE_NO,
            clause="Regulation 20",
            page=20,
            quote_span="Discretionary guideline",
        ),
        validity=Validity(published=PUBLICATION_DATE, commences=COMMENCEMENT_DATE),
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(type="discretionary", text="Discretionary", impact_categories=["general"]),
        verification=Verification(status="NON_COMPILABLE", extraction_model="test", agreement=False),
    )
    profile = BusinessProfile(business_id="BIZ-GAZETTE-008")
    res = evaluate_rule(rule=unsupp_rule, profile=profile, as_at_date="2026-07-15")
    assert res.status == OutcomeStatus.UNSUPPORTED


def test_version_preservation_on_amendment(test_db):
    """Task 5: Amending a rule preserves prior version snapshot in verification_report.version_history."""
    doc_orm = SourceDocumentORM(
        id="doc_ver_test",
        title=GAZETTE_DOC_TITLE,
        authority=GAZETTE_AUTHORITY,
        instrument_type="gazette_regulation",
        file_path=str(GAZETTE_PDF_PATH),
        file_size_bytes=len(GAZETTE_PDF_PATH.read_bytes()),
        sha256_hash="test_version_hash_" + "0" * 46,
        page_count=1,
        extraction_status="SUCCESS",
    )
    clause_orm = ClauseORM(
        clause_id="CLAUSE-VER-01",
        version_number=1,
        document_id="doc_ver_test",
        clause_number="Regulation 3",
        text=VERBATIM_RETAIL_QUOTE,
        start_page=1,
        end_page=1,
    )
    original_applies = {"all": [{"field": "activity", "op": "eq", "value": "food_manufacturing"}]}
    rule_orm = RuleORM(
        rule_id="RULE-VER-001",
        clause_id="CLAUSE-VER-01",
        clause_version=1,
        outcome_type="STANDARD",
        applies_if=original_applies,
        obligation={"type": "labelling", "text": "Original", "impact_categories": []},
        validity={"published": PUBLICATION_DATE, "commences": COMMENCEMENT_DATE},
        source={"clause": "Regulation 3", "instrument": GAZETTE_DOC_TITLE, "authority": GAZETTE_AUTHORITY, "gazette_no": GAZETTE_NO, "page": 1, "quote_span": VERBATIM_RETAIL_QUOTE},
        review_status="PENDING_REVIEW",
    )
    test_db.add(doc_orm)
    test_db.commit()
    test_db.add(clause_orm)
    test_db.commit()
    test_db.add(rule_orm)
    test_db.commit()

    review_svc = ReviewService(test_db)
    amended_applies = {
        "all": [
            {"field": "activity", "op": "eq", "value": "food_manufacturing"},
            {"field": "products.prepackaged", "op": "eq", "value": True},
        ]
    }
    review_svc.submit_review(
        rule_id="RULE-VER-001",
        reviewer_id="lead_researcher_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_AMENDED,
        rationale="Added prepackaged requirement per Regulation 3 text.",
        amendments={"applies_if": amended_applies},
    )

    test_db.refresh(rule_orm)
    assert rule_orm.applies_if == amended_applies
    v_rep = rule_orm.verification_report
    assert v_rep is not None
    assert "version_history" in v_rep
    assert len(v_rep["version_history"]) == 1
    assert v_rep["version_history"][0]["prior_state"]["applies_if"] == original_applies


# ===========================================================================
# 6. Authoritative Seed & Repository Round-Trip Tests (Milestone Repair)
# ===========================================================================

def test_real_slice_seeding_and_repository_roundtrip(test_db):
    """Task 3.A: Test seed_real_slice() and verify full repository roundtrip with disclosures."""
    seed_real_slice(session=test_db)

    # 1. Authoritative Gazette document verification
    doc = test_db.query(SourceDocumentORM).filter_by(id="doc_gazette_2494_47").first()
    assert doc is not None, "Promulgated Gazette document missing after seed_real_slice()"
    assert "2494/47" in doc.gazette_no
    assert doc.instrument_type == "gazette_regulation"

    # 2. Both rules present
    rules = test_db.query(RuleORM).filter(
        RuleORM.rule_id.in_(["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"])
    ).all()
    assert len(rules) == 2, f"Expected 2 real-source rules, found {len(rules)}"

    # 3. Retrieve through actual repository implementation
    repo = PostgresRegulatoryRepository(test_db)
    retail_rules = repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3"])
    b2b_rules = repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3-B2B"])

    assert len(retail_rules) == 1
    assert len(b2b_rules) == 1
    retail_rule = retail_rules[0]
    b2b_rule = b2b_rules[0]

    # 4. Provenance and source quote verification
    assert "Food (Labelling and Advertising) Regulations 2026" in retail_rule.source.instrument
    assert "2494/47" in retail_rule.source.gazette_no
    assert retail_rule.source.page == 1
    assert "A person shall not import, transport" in retail_rule.source.quote_span

    assert "Food (Labelling and Advertising) Regulations 2026" in b2b_rule.source.instrument
    assert "2494/47" in b2b_rule.source.gazette_no
    assert b2b_rule.source.page == 2
    assert "business-to-business food products" in b2b_rule.source.quote_span

    # 5. Review integrity on ORM
    retail_orm = test_db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3").first()
    b2b_orm = test_db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3-B2B").first()
    assert retail_orm is not None and retail_orm.review_status == "APPROVED"
    assert retail_orm.is_gold_rule is False
    assert b2b_orm is not None and b2b_orm.review_status == "APPROVED"
    assert b2b_orm.is_gold_rule is False
    assert retail_rule.verification.status == "APPROVED"
    assert b2b_rule.verification.status == "APPROVED"

    # 6. Complete B2B statutory disclosures survive persistence and retrieval
    expected_disclosures = [
        "common_name",
        "trade_name",
        "net_contents",
        "date_of_manufacture",
        "date_of_expiry",
        "batch_number",
        "manufacturer_details",
        "distributor_details",
        "country_of_origin",
        "ingredients_list",
        "not_for_retail_sale_statement",
    ]
    assert b2b_rule.obligation.disclosures is not None, "B2B obligation disclosures lost in roundtrip!"
    assert b2b_rule.obligation.disclosures == expected_disclosures, (
        f"Disclosure list mismatch: {b2b_rule.obligation.disclosures}"
    )


def test_real_slice_seeding_idempotence(test_db):
    """Task 3.A: Ensure repeated seeding is deterministic and idempotent without duplicate entries."""
    seed_real_slice(session=test_db)
    count_docs_1 = test_db.query(SourceDocumentORM).count()
    count_clauses_1 = test_db.query(ClauseORM).count()
    count_rules_1 = test_db.query(RuleORM).count()
    count_audits_1 = test_db.query(HumanReviewAuditORM).count()

    # Second seed invocation on the same database
    seed_real_slice(session=test_db)
    count_docs_2 = test_db.query(SourceDocumentORM).count()
    count_clauses_2 = test_db.query(ClauseORM).count()
    count_rules_2 = test_db.query(RuleORM).count()
    count_audits_2 = test_db.query(HumanReviewAuditORM).count()

    assert count_docs_1 == count_docs_2
    assert count_clauses_1 == count_clauses_2
    assert count_rules_1 == count_rules_2
    assert count_audits_1 == count_audits_2


def test_regression_disclosures_persistence_roundtrip(test_db):
    """Task 1: Regression test proving Obligation.disclosures survives Domain -> ORM -> DB -> Domain."""
    seed_real_slice(session=test_db)
    repo = PostgresRegulatoryRepository(test_db)

    sample_disclosures = [
        "common_name",
        "batch_number",
        "date_of_expiry",
        "not_for_retail_sale_statement",
    ]
    test_rule = Rule(
        rule_id="RULE-REGRESSION-DISCLOSURE-001",
        clause_id="CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3",
        clause_version=1,
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(
            type="b2b_labelling",
            text="Test B2B obligation with disclosures",
            impact_categories=["label_compliance"],
            disclosures=sample_disclosures,
        ),
        validity=Validity(published="2026-06-26", commences="2026-07-01"),
        source=Source(
            clause="Regulation 3",
            instrument="Food Regulations 2026",
            authority="Food Advisory Committee",
            gazette_no="2494/47",
            page=2,
            quote_span="Test quote span",
        ),
        verification=Verification(
            status="APPROVED",
            extraction_model="manual_audit",
            agreement=True,
        ),
    )

    # 1. Convert to ORM dict
    orm_dict = rule_domain_to_orm_dict(test_rule)
    assert "disclosures" in orm_dict["obligation"], "disclosures missing from rule_domain_to_orm_dict"
    assert orm_dict["obligation"]["disclosures"] == sample_disclosures

    # 2. Persist in database
    rule_orm = RuleORM(**orm_dict)
    test_db.add(rule_orm)
    test_db.commit()

    # 3. Reload from database through repository
    reloaded_rules = repo.get_rules_by_ids(["RULE-REGRESSION-DISCLOSURE-001"])
    assert len(reloaded_rules) == 1
    reloaded_rule = reloaded_rules[0]
    assert reloaded_rule.obligation.disclosures == sample_disclosures, (
        f"Reloaded disclosures mismatch: {reloaded_rule.obligation.disclosures} != {sample_disclosures}"
    )

    # 4. Also verify backward compatibility: rule with null disclosures
    rule_null_disc = Rule(
        rule_id="RULE-REGRESSION-NULL-DISC",
        clause_id="CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3",
        clause_version=1,
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(
            type="labelling",
            text="Standard labelling without disclosures",
            impact_categories=["labelling"],
            disclosures=None,
        ),
        validity=Validity(published="2026-06-26", commences="2026-07-01"),
        source=Source(
            clause="Regulation 3",
            instrument="Food Regulations 2026",
            authority="Food Advisory Committee",
            gazette_no="2494/47",
            page=1,
            quote_span="Standard retail quote",
        ),
        verification=Verification(
            status="APPROVED",
            extraction_model="manual_audit",
            agreement=True,
        ),
    )
    test_db.add(RuleORM(**rule_domain_to_orm_dict(rule_null_disc)))
    test_db.commit()

    reloaded_null_list = repo.get_rules_by_ids(["RULE-REGRESSION-NULL-DISC"])
    assert len(reloaded_null_list) == 1
    assert reloaded_null_list[0].obligation.disclosures is None


# ===========================================================================
# 7. B2B Impact Mapping & Legal Distinction Tests
# ===========================================================================

def test_b2b_impact_mapping_disclosures_and_no_trilingual(seeded_real_db):
    """Task 2: Verify B2B impact mapping surfaces 10 disclosures + bold statement without trilingual contradiction."""
    repo = PostgresRegulatoryRepository(seeded_real_db)
    b2b_rules = repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3-B2B"])
    assert len(b2b_rules) == 1
    b2b_rule = b2b_rules[0]

    impact = map_impact(b2b_rule)
    assert impact is not None

    action_text = " ".join(impact.action_items).lower()

    # CRITICAL: Trilingual requirement MUST NOT be emitted for B2B food products
    assert "trilingual" not in action_text, "Found contradictory trilingual instruction in B2B action items!"
    assert "mandatory trilingual" not in action_text
    assert not any("mandatory trilingual" in a.lower() for a in impact.action_items)

    # Verify specific B2B obligations are present
    assert any("either of the three languages" in a.lower() or "sinhala, tamil, or english" in a.lower() for a in impact.action_items)
    assert any("not for retail sale" in a.lower() and "3 mm" in a.lower() for a in impact.action_items)
    assert any("batch number" in a.lower() for a in impact.action_items)
    assert any("date of manufacture" in a.lower() for a in impact.action_items)
    assert any("date of expiry" in a.lower() for a in impact.action_items)
    assert any("country of origin" in a.lower() for a in impact.action_items)
    assert any("complete list of ingredients" in a.lower() for a in impact.action_items)
    assert any("net contents" in a.lower() for a in impact.action_items)

    # Verify affected documents and activities
    assert any("business-to-business product packaging" in d.lower() for d in impact.affected_documents)
    assert any("supplementary label specifications" in d.lower() for d in impact.affected_documents)
    assert any("b2b product packaging design" in a.lower() for a in impact.affected_activities)

    # Verify evidence and clause references
    assert impact.clause_reference == "Regulation 3, Proviso (b)"
    assert "Gazette Extraordinary No. 2494/47" in impact.document_name


# ===========================================================================
# 8. FastAPI API Integration Tests (POST /analysis)
# ===========================================================================

def test_api_analysis_endpoint_retail_profile(client_with_real_slice):
    """Task 3.B.1: Retail profile activates retail rule and does not activate B2B rule."""
    payload = {
        "clause_ids": ["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
        "business_profile": {
            "business_id": "BIZ-RETAIL-01",
            "activity": "food_manufacturing",
            "packaged_in_presence_of_purchaser": False,
            "market": {"b2b_only": False},
            "products": [
                {
                    "name": "Bottled Mixed Fruit Jam",
                    "prepackaged": True,
                    "market_channel": "retail",
                }
            ],
        },
    }
    response = client_with_real_slice.post("/analysis", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    eval_map = {e["rule_id"]: e for e in data["evaluations"]}
    assert eval_map["RULE-FCAU-2494-47-REG-3"]["status"] == OutcomeStatus.APPLICABLE.value
    assert eval_map["RULE-FCAU-2494-47-REG-3-B2B"]["status"] == OutcomeStatus.NOT_APPLICABLE.value

    # Retail action items should include labelling
    assert len(data["action_checklist"]) > 0
    assert any("trilingual" in a.lower() for a in data["action_checklist"])


def test_api_analysis_endpoint_b2b_profile(client_with_real_slice):
    """Task 3.B.2: B2B profile activates B2B rule, exposes B2B obligations, and omits retail trilingual action."""
    payload = {
        "clause_ids": ["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
        "business_profile": {
            "business_id": "BIZ-B2B-01",
            "activity": "food_manufacturing",
            "packaged_in_presence_of_purchaser": False,
            "market": {"b2b_only": True},
            "products": [
                {
                    "name": "Industrial Bulk Mango Puree (200L Drum)",
                    "prepackaged": True,
                    "market_channel": "b2b",
                }
            ],
        },
    }
    response = client_with_real_slice.post("/analysis", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    eval_map = {e["rule_id"]: e for e in data["evaluations"]}
    assert eval_map["RULE-FCAU-2494-47-REG-3"]["status"] == OutcomeStatus.NOT_APPLICABLE.value
    assert eval_map["RULE-FCAU-2494-47-REG-3-B2B"]["status"] == OutcomeStatus.APPLICABLE.value

    # Check action items: must NOT have contradictory retail trilingual requirement
    actions_joined = " ".join(data["action_checklist"]).lower()
    assert "trilingual" not in actions_joined
    assert "mandatory trilingual" not in actions_joined
    assert not any("mandatory trilingual" in a.lower() for a in data["action_checklist"])

    # Must contain specific B2B obligations
    assert any("either of the three languages" in a.lower() or "sinhala, tamil, or english" in a.lower() for a in data["action_checklist"])
    assert any("not for retail sale" in a.lower() and "3 mm" in a.lower() for a in data["action_checklist"])
    assert any("batch number" in a.lower() for a in data["action_checklist"])


def test_api_analysis_endpoint_missing_market_channel(client_with_real_slice):
    """Task 3.B.3: Missing market-channel returns CONDITIONAL_MISSING_DATA without guessing."""
    payload = {
        "clause_ids": ["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
        "business_profile": {
            "business_id": "BIZ-UNKNOWN-CHANNEL",
            "activity": "food_manufacturing",
            "packaged_in_presence_of_purchaser": False,
            "market": None,
            "products": [
                {
                    "name": "Packaged Curry Powder",
                    "prepackaged": True,
                }
            ],
        },
    }
    response = client_with_real_slice.post("/analysis", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    eval_map = {e["rule_id"]: e for e in data["evaluations"]}
    assert eval_map["RULE-FCAU-2494-47-REG-3"]["status"] == OutcomeStatus.CONDITIONAL_MISSING_DATA.value
    assert eval_map["RULE-FCAU-2494-47-REG-3-B2B"]["status"] == OutcomeStatus.CONDITIONAL_MISSING_DATA.value
    assert "market.b2b_only" in eval_map["RULE-FCAU-2494-47-REG-3"]["missing_fields"]
    assert "market.b2b_only" in data["missing_fields"]


def test_api_analysis_endpoint_b2b_missing_disclosure_applicability_contract(client_with_real_slice):
    """Task 3.B.4: Missing disclosure on product label; verify applicability vs compliance boundary.

    The API reports regulatory APPLICABILITY and mandated disclosures; it does NOT claim
    the product label has been audited or certified compliant.
    """
    payload = {
        "clause_ids": ["RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
        "business_profile": {
            "business_id": "BIZ-B2B-MISSING-LABEL-DISCLOSURE",
            "activity": "food_manufacturing",
            "packaged_in_presence_of_purchaser": False,
            "market": {"b2b_only": True},
            "products": [
                {
                    "name": "Bulk Desiccated Coconut",
                    "prepackaged": True,
                    "market_channel": "b2b",
                }
            ],
        },
    }
    response = client_with_real_slice.post("/analysis", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    b2b_eval = data["evaluations"][0]
    # The rule is APPLICABLE to this B2B food manufacturer
    assert b2b_eval["status"] == OutcomeStatus.APPLICABLE.value

    # Action items state mandatory disclosures that must be present
    checklist = " ".join(data["action_checklist"])
    assert "Batch number" in checklist
    assert "Date of expiry" in checklist

    # The API contract does NOT claim label compliance verification
    assert "label_verified_compliant" not in data
    assert "compliance_certificate" not in data


def test_api_analysis_endpoint_b2b_marking_problem(client_with_real_slice):
    """Task 3.B.5: Report applicable obligation without inventing unauthorized legal forfeiture penalty."""
    payload = {
        "clause_ids": ["RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
        "business_profile": {
            "business_id": "BIZ-B2B-MARKING-QUERY",
            "activity": "food_manufacturing",
            "packaged_in_presence_of_purchaser": False,
            "market": {"b2b_only": True},
            "products": [
                {
                    "name": "Industrial Baker Yeast 20kg",
                    "prepackaged": True,
                    "market_channel": "b2b",
                }
            ],
        },
    }
    response = client_with_real_slice.post("/analysis", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    b2b_eval = data["evaluations"][0]
    assert b2b_eval["status"] == OutcomeStatus.APPLICABLE.value

    # Action surfaces the statutory >= 3 mm bold marking requirement
    actions_joined = " ".join(data["action_checklist"])
    assert "Not for retail sale" in actions_joined
    assert "3 mm" in actions_joined

    # Does not invent an unverified legal penalty claiming loss of exception
    assert "forfeited" not in actions_joined.lower()
    assert "criminal" not in actions_joined.lower()


def test_api_analysis_endpoint_out_of_scope_profile(client_with_real_slice):
    """Task 3.B.6: Out-of-scope profile activates neither retail nor B2B rule."""
    payload = {
        "clause_ids": ["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
        "business_profile": {
            "business_id": "BIZ-FARMING-01",
            "activity": "farming_and_agriculture",
            "packaged_in_presence_of_purchaser": False,
            "market": {"b2b_only": False},
            "products": [
                {
                    "name": "Harvested Raw Paddy Rice",
                    "prepackaged": False,
                }
            ],
        },
    }
    response = client_with_real_slice.post("/analysis", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    eval_map = {e["rule_id"]: e for e in data["evaluations"]}
    assert eval_map["RULE-FCAU-2494-47-REG-3"]["status"] == OutcomeStatus.NOT_APPLICABLE.value
    assert eval_map["RULE-FCAU-2494-47-REG-3-B2B"]["status"] == OutcomeStatus.NOT_APPLICABLE.value
    assert data["applicable_rules_count"] == 0
    assert len(data["action_checklist"]) == 0


# ===========================================================================
# 9. Test Independence Assertions (Task 3.C)
# ===========================================================================

def test_test_independence_fails_if_b2b_rule_missing(test_db):
    """Task 3.C: Assert test failure occurs if B2B rule is absent from database."""
    seed_real_slice(session=test_db)
    b2b_orm = test_db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3-B2B").first()
    assert b2b_orm is not None
    test_db.delete(b2b_orm)
    test_db.commit()

    repo = PostgresRegulatoryRepository(test_db)
    assert len(repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3"])) == 1
    assert len(repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3-B2B"])) == 0


def test_test_independence_fails_if_disclosures_removed_from_serialization():
    """Task 3.C: Proves that dropping disclosures from ORM serialization results in disclosure loss."""
    sample_rule = Rule(
        rule_id="RULE-TEMP-TEST",
        clause_id="CLAUSE-TEMP",
        clause_version=1,
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(
            type="b2b_labelling",
            text="B2B obligations",
            impact_categories=["label_compliance"],
            disclosures=["common_name", "batch_number"],
        ),
        validity=Validity(published="2026-06-26", commences="2026-07-01"),
        source=Source(
            clause="Reg 3",
            instrument="Food Regs",
            authority="FAC",
            gazette_no="2494/47",
            page=2,
            quote_span="quote",
        ),
        verification=Verification(
            status="APPROVED",
            extraction_model="manual_audit",
            agreement=True,
        ),
    )

    orm_dict = rule_domain_to_orm_dict(sample_rule)
    # Simulate defect: disclosures stripped from obligation dictionary
    defective_orm_dict = dict(orm_dict)
    defective_obl = dict(defective_orm_dict["obligation"])
    defective_obl.pop("disclosures", None)
    defective_orm_dict["obligation"] = defective_obl

    # Reconstruct ORM model and deserialize back to domain Rule
    orm_model = RuleORM(**defective_orm_dict)
    domain_from_defective = rule_orm_to_domain(orm_model)

    assert domain_from_defective.obligation.disclosures is None, (
        "Expected disclosure loss when disclosures field is missing from ORM data"
    )


def test_test_independence_fails_if_trilingual_reintroduced_to_b2b():
    """Task 3.C: Validates that map_impact strictly rejects generic trilingual labelling on B2B rules."""
    b2b_rule = Rule(
        rule_id="RULE-MOCK-B2B",
        clause_id="CLAUSE-MOCK",
        clause_version=1,
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(
            type="b2b_labelling",
            text="B2B statutory labelling requirements",
            impact_categories=["labelling"],
            disclosures=["common_name", "batch_number"],
        ),
        validity=Validity(published="2026-06-26", commences="2026-07-01"),
        source=Source(
            clause="Regulation 3, Proviso (b)",
            instrument="Food (Labelling and Advertising) Regulations 2026",
            authority="Food Advisory Committee",
            gazette_no="2494/47",
            page=2,
            quote_span="B2B statutory quote",
        ),
        verification=Verification(
            status="APPROVED",
            extraction_model="manual_audit",
            agreement=True,
        ),
    )

    impact = map_impact(b2b_rule)
    # Direct negative check: generic trilingual action must NEVER appear
    generic_retail_action = (
        "Design or update product label layout to include mandatory trilingual text (Sinhala, Tamil, English), "
        "batch number, expiry date, net volume/weight, and manufacturer registration details."
    )
    assert generic_retail_action not in impact.action_items

