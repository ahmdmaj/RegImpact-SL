"""Milestone: First Verified Real-Source Vertical Slice.

Verifies and demonstrates an end-to-end, auditable pipeline using a genuine
official Sri Lankan regulatory source:
  - Document: Food (Labelling and Advertising) Regulations 2026
    (Official draft publication corresponding to Gazette Extraordinary No. 2494/47)
  - SHA-256 Hash: c70b5668131b76ff206897ef391cb3402bb4bf6be39a76ad1400d24c07330142
  - Target Clause: Regulation 2 (General labelling mandate for packaged food)
  - Coordinates: Page 1, character offsets [242, 1514]
  - Grounding: Exact verbatim quote span match against raw PDF text
  - Provenance: Genuinely distinguishes candidate, verified, and human-reviewed states
  - Evaluation: Deterministic 3-valued Kleene logic covering all legal branches
"""

import datetime
import hashlib
from pathlib import Path
import pytest
import pymupdf

from backend.src.db.models import (
    Base,
    ClauseORM,
    DocumentPageORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
)
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.review import (
    DECISION_APPROVED,
    DECISION_AMENDED,
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_EXPERT_ADJUDICATOR,
    ReviewService,
)
from backend.src.engine.verifier import RuleVerifier
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
# Constants for the Real Regulatory Source Vertical Slice
# ---------------------------------------------------------------------------

REAL_PDF_PATH = Path("backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
EXPECTED_SHA256 = "c70b5668131b76ff206897ef391cb3402bb4bf6be39a76ad1400d24c07330142"
EXPECTED_PAGE_COUNT = 22

DOC_ID = "doc_labelling_regulations_final_2026"
DOC_TITLE = "Food (Labelling and Advertising) Regulations 2026"
DOC_AUTHORITY = "Food Advisory Committee / Ministry of Health"
DOC_GAZETTE_NO = "Gazette Extraordinary No. 2494/47"

CLAUSE_ID = "CLAUSE-DOC_LABELLING_REGULATIONS_FINAL_2026-REGULATION-2"
CLAUSE_NUMBER = "Regulation 2"
CLAUSE_PAGE = 1
CLAUSE_CHAR_START = 242
CLAUSE_CHAR_END = 1514

VERBATIM_QUOTE_SPAN = (
    "A person shall not import, transport, distribute, store, sell, offer for sale, expose or keep for sale "
    "or advertise, any \nfood contained in a package or container, unless such package or container is "
    "labelled in accordance with these \nregulations:"
)

COMMENCEMENT_DATE = "2026-07-01"
PUBLICATION_DATE = "2026-07-01"


@pytest.fixture
def test_db():
    """In-memory SQLite database session factory for isolated testing."""
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)
    session = session_factory()
    yield session
    session.close()


# ===========================================================================
# 1. Document Provenance and Reproducible Hash
# ===========================================================================

def test_real_source_document_provenance_and_hash():
    """Acceptance Test 1: Real source PDF exists with verified, reproducible SHA-256 hash."""
    assert REAL_PDF_PATH.exists(), f"Source PDF missing at {REAL_PDF_PATH}"
    
    file_bytes = REAL_PDF_PATH.read_bytes()
    computed_hash = hashlib.sha256(file_bytes).hexdigest()
    
    assert computed_hash == EXPECTED_SHA256, (
        f"Hash mismatch! Expected {EXPECTED_SHA256}, got {computed_hash}"
    )
    
    doc = pymupdf.open(str(REAL_PDF_PATH))
    assert len(doc) == EXPECTED_PAGE_COUNT
    
    # Verify Page 1 contains the authoritative title and citation
    p1_text = doc[0].get_text()
    assert "Food (Labelling and Advertising) Regulations 2026" in p1_text
    assert "come into operation \non July 1, 2026" in p1_text
    doc.close()


# ===========================================================================
# 2. Traceability and Grounding to Exact Source Coordinates
# ===========================================================================

def test_real_clause_text_grounding_and_location():
    """Acceptance Test 2: Target clause is traceable to exact page and character offsets."""
    doc = pymupdf.open(str(REAL_PDF_PATH))
    p1_text = doc[0].get_text()
    doc.close()
    
    # Locate Regulation 2 in the raw text
    reg2_start = p1_text.find("2. A person shall not import")
    reg3_start = p1_text.find("3. (1)")
    
    assert reg2_start == CLAUSE_CHAR_START
    assert reg3_start == CLAUSE_CHAR_END
    
    clause_full_text = p1_text[reg2_start:reg3_start].strip()
    assert clause_full_text.startswith("2. A person shall not import")
    assert "Business-to-business food products" in clause_full_text
    assert "weighed, counted, or measured in the presence of the \npurchaser" in clause_full_text
    
    # Verify quote span is an exact, uncorrupted substring of Page 1
    quote_pos = p1_text.find(VERBATIM_QUOTE_SPAN)
    assert quote_pos != -1, "Verbatim quote span not found in raw PDF page text!"
    assert quote_pos >= CLAUSE_CHAR_START and quote_pos < CLAUSE_CHAR_END


# ===========================================================================
# 3. Typed Rule AST Compilation and Legal Structure
# ===========================================================================

def test_typed_rule_ast_preserves_legal_structure():
    """Acceptance Test 3: AST preserves legal obligation, scope, conditions, and dates."""
    rule = Rule(
        rule_id="RULE-FCAU-REAL-2026-REG-2",
        source=Source(
            instrument=DOC_TITLE,
            authority=DOC_AUTHORITY,
            gazette_no=DOC_GAZETTE_NO,
            clause=CLAUSE_NUMBER,
            page=CLAUSE_PAGE,
            quote_span=VERBATIM_QUOTE_SPAN,
        ),
        validity=Validity(
            published=PUBLICATION_DATE,
            commences=COMMENCEMENT_DATE,
        ),
        applies_if=AppliesIf(
            all=[
                Condition(
                    field="activity",
                    op="in",
                    value=["food_manufacturing", "catering", "retail_trade", "distribution", "import", "storage"],
                ),
                Condition(
                    field="products.prepackaged",
                    op="eq",
                    value=True,
                ),
            ]
        ),
        exceptions=[
            Condition(field="packaged_in_presence_of_purchaser", op="eq", value=True),
            Condition(field="market.b2b_only", op="eq", value=True),
        ],
        obligation=Obligation(
            type="labelling",
            text="Food contained in a package or container must be labelled in accordance with the Food (Labelling and Advertising) Regulations 2026.",
            impact_categories=["labelling", "packaging", "commercial_distribution"],
        ),
        verification=Verification(
            status="PENDING_REVIEW",
            extraction_model="claude-3-5-sonnet",
            agreement=True,
            reason="Extracted from Page 1 of Food (Labelling and Advertising) Regulations 2026.",
        ),
    )
    
    # Structural AST integrity assertions
    assert rule.source.page == 1
    assert rule.validity.commences == "2026-07-01"
    assert len(rule.applies_if.all) == 2
    assert len(rule.exceptions) == 2
    assert rule.obligation.type == "labelling"
    assert "labelling" in rule.obligation.impact_categories


# ===========================================================================
# 4. Provenance Distinction: Candidate vs Technically Verified vs Human-Approved
# ===========================================================================

def test_provenance_distinction_draft_verified_reviewed(test_db):
    """Acceptance Test 4: System enforces distinction between candidate, verified, and human review."""
    # Step A: Register source document in database
    doc_orm = SourceDocumentORM(
        id=DOC_ID,
        title=DOC_TITLE,
        authority=DOC_AUTHORITY,
        instrument_type="regulation",
        gazette_no=DOC_GAZETTE_NO,
        file_path=str(REAL_PDF_PATH),
        file_size_bytes=len(REAL_PDF_PATH.read_bytes()),
        sha256_hash=EXPECTED_SHA256,
        page_count=EXPECTED_PAGE_COUNT,
        extraction_status="SUCCESS",
        extraction_tool="pymupdf",
    )
    test_db.add(doc_orm)
    test_db.commit()

    # Step B: Anchor clause
    clause_orm = ClauseORM(
        clause_id=CLAUSE_ID,
        version_number=1,
        document_id=DOC_ID,
        clause_number=CLAUSE_NUMBER,
        text=VERBATIM_QUOTE_SPAN,
        start_page=CLAUSE_PAGE,
        end_page=CLAUSE_PAGE,
        char_start=CLAUSE_CHAR_START,
        char_end=CLAUSE_CHAR_END,
        is_compilable=True,
    )
    test_db.add(clause_orm)
    test_db.commit()

    # Step C: State 1 - Candidate Generated Rule (DRAFT/PENDING_REVIEW)
    candidate_rule_orm = RuleORM(
        rule_id="RULE-FCAU-REAL-2026-REG-2",
        clause_id=CLAUSE_ID,
        clause_version=1,
        outcome_type="STANDARD",
        applies_if={
            "all": [
                {"field": "activity", "op": "in", "value": ["food_manufacturing", "catering", "retail_trade"]},
                {"field": "products.prepackaged", "op": "eq", "value": True},
            ]
        },
        exceptions=[
            {"field": "packaged_in_presence_of_purchaser", "op": "eq", "value": True},
            {"field": "market.b2b_only", "op": "eq", "value": True},
        ],
        obligation={
            "type": "labelling",
            "text": "Food contained in a package or container must be labelled in accordance with the Food (Labelling and Advertising) Regulations 2026.",
            "impact_categories": ["labelling", "packaging"],
        },
        validity={"published": PUBLICATION_DATE, "commences": COMMENCEMENT_DATE},
        source={
            "clause": CLAUSE_NUMBER,
            "instrument": DOC_TITLE,
            "authority": DOC_AUTHORITY,
            "gazette_no": DOC_GAZETTE_NO,
            "page": CLAUSE_PAGE,
            "quote_span": VERBATIM_QUOTE_SPAN,
        },
        review_status="PENDING_REVIEW",
        is_gold_rule=False,  # NOT human-approved yet
    )
    test_db.add(candidate_rule_orm)
    test_db.commit()

    # Verify State 1: Candidate is NOT approved
    persisted = test_db.get(RuleORM, "RULE-FCAU-REAL-2026-REG-2")
    assert persisted.review_status == "PENDING_REVIEW"
    assert persisted.is_gold_rule is False
    assert len(persisted.audit_log) == 0

    # Step D: State 2 - Technical Verification
    verifier = RuleVerifier()
    rule_domain = Rule(
        rule_id=persisted.rule_id,
        source=Source(**persisted.source),
        validity=Validity(**persisted.validity),
        applies_if=AppliesIf(**persisted.applies_if),
        exceptions=persisted.exceptions,
        obligation=Obligation(**persisted.obligation),
        verification=Verification(status="PENDING_REVIEW", extraction_model="test", agreement=True),
    )
    doc = pymupdf.open(str(REAL_PDF_PATH))
    p1_text = doc[0].get_text()
    doc.close()
    v_report = verifier.verify(rule_domain, source_text=p1_text)
    assert v_report.is_valid is True
    assert v_report.status == "verified"
    
    # Crucial: Technical verification DOES NOT alter legal review status to APPROVED
    assert persisted.review_status == "PENDING_REVIEW"

    # Step E: State 3 - Human Review Step with Genuine Reviewer Role
    review_svc = ReviewService(test_db)
    review_svc.submit_review(
        rule_id="RULE-FCAU-REAL-2026-REG-2",
        reviewer_id="researcher_engineer_01",
        reviewer_role=ROLE_PRIMARY_ANNOTATOR,
        decision=DECISION_APPROVED,
        rationale=(
            "Verified against Page 1 of official Food (Labelling and Advertising) Regulations 2026. "
            "Universal packaged food mandate accurately captured with purchaser-presence and B2B exceptions. "
            "Note: Independent legal expert adjudication is pending."
        ),
    )
    test_db.refresh(persisted)
    assert persisted.review_status == "APPROVED"
    assert persisted.is_gold_rule is False  # Primary annotator approval is NOT gold expert adjudication
    assert len(persisted.audit_log) == 1
    audit = persisted.audit_log[0]
    assert audit.reviewer_id == "researcher_engineer_01"
    assert audit.reviewer_role == ROLE_PRIMARY_ANNOTATOR
    assert audit.decision == "APPROVED"


# ===========================================================================
# 5. Deterministic Engine Evaluation on Actual Legal Conditions
# ===========================================================================

@pytest.fixture
def base_real_rule():
    """Rule object for Regulation 2."""
    return Rule(
        rule_id="RULE-FCAU-REAL-2026-REG-2",
        source=Source(
            instrument=DOC_TITLE,
            authority=DOC_AUTHORITY,
            gazette_no=DOC_GAZETTE_NO,
            clause=CLAUSE_NUMBER,
            page=CLAUSE_PAGE,
            quote_span=VERBATIM_QUOTE_SPAN,
        ),
        validity=Validity(
            published=PUBLICATION_DATE,
            commences=COMMENCEMENT_DATE,
        ),
        applies_if=AppliesIf(
            all=[
                Condition(
                    field="activity",
                    op="in",
                    value=["food_manufacturing", "catering", "retail_trade"],
                ),
                Condition(
                    field="products.prepackaged",
                    op="eq",
                    value=True,
                ),
            ]
        ),
        exceptions=[
            Condition(field="packaged_in_presence_of_purchaser", op="eq", value=True),
            Condition(field="market.b2b_only", op="eq", value=True),
        ],
        obligation=Obligation(
            type="labelling",
            text="Food contained in a package or container must be labelled in accordance with the Food (Labelling and Advertising) Regulations 2026.",
            impact_categories=["labelling", "packaging"],
        ),
        verification=Verification(
            status="APPROVED",
            extraction_model="claude-3-5-sonnet",
            agreement=True,
        ),
    )


def test_deterministic_evaluation_applicable_case(base_real_rule):
    """Case 1: Packaged food producer post-commencement -> APPLICABLE."""
    profile = BusinessProfile(
        business_id="BIZ-REAL-001",
        activity="food_manufacturing",
        products=[Product(category="spices", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": False},
    )
    result = evaluate_rule(rule=base_real_rule, profile=profile, as_at_date="2026-07-15")
    assert result.status == OutcomeStatus.APPLICABLE
    assert result.missing_fields == []
    assert len(result.evaluation_trace) >= 2
    # Verify trace contains exact field comparisons
    act_trace = next(t for t in result.evaluation_trace if t["field"] == "activity")
    assert act_trace["result"] == "TRUE"
    pkg_trace = next(t for t in result.evaluation_trace if t["field"] == "products.prepackaged")
    assert pkg_trace["result"] == "TRUE"


def test_deterministic_evaluation_purchaser_presence_exception(base_real_rule):
    """Case 2: Custom bulk packaging in presence of purchaser -> NOT_APPLICABLE (Exception)."""
    profile = BusinessProfile(
        business_id="BIZ-REAL-002",
        activity="retail_trade",
        products=[Product(category="grains", prepackaged=True)],
        packaged_in_presence_of_purchaser=True,  # Exception condition triggered
        market={"b2b_only": False},
    )
    result = evaluate_rule(rule=base_real_rule, profile=profile, as_at_date="2026-07-15")
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert "exception condition met" in result.reason.lower()


def test_deterministic_evaluation_b2b_exception(base_real_rule):
    """Case 3: Business-to-business food products -> NOT_APPLICABLE under general retail rule."""
    profile = BusinessProfile(
        business_id="BIZ-REAL-003",
        activity="food_manufacturing",
        products=[Product(category="bulk_flour", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": True},  # B2B exception triggered
    )
    result = evaluate_rule(rule=base_real_rule, profile=profile, as_at_date="2026-07-15")
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert "exception condition met" in result.reason.lower()


def test_deterministic_evaluation_missing_packaging_data(base_real_rule):
    """Case 4: Prepackaged field is UNKNOWN -> CONDITIONAL_MISSING_DATA."""
    profile = BusinessProfile(
        business_id="BIZ-REAL-004",
        activity="food_manufacturing",
        products=[Product(category="bakery", prepackaged=None)],  # UNKNOWN
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": False},
    )
    result = evaluate_rule(rule=base_real_rule, profile=profile, as_at_date="2026-07-15")
    assert result.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "products.prepackaged" in result.missing_fields
    assert "unknown business profile fields" in result.reason.lower()


def test_deterministic_evaluation_temporal_prior_to_commencement(base_real_rule):
    """Case 5: Evaluation date prior to July 1, 2026 -> NOT_APPLICABLE."""
    profile = BusinessProfile(
        business_id="BIZ-REAL-005",
        activity="food_manufacturing",
        products=[Product(category="confectionery", prepackaged=True)],
        packaged_in_presence_of_purchaser=False,
        market={"b2b_only": False},
    )
    result = evaluate_rule(rule=base_real_rule, profile=profile, as_at_date="2026-05-01")
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert result.temporal_status == "NOT_YET_IN_FORCE"
    assert "not yet in force" in result.reason.lower()


def test_deterministic_evaluation_conditional_rule():
    """Case 6: Rule with outcome_type='CONDITIONAL_RULE' -> CONDITIONAL_RULE outcome."""
    conditional_rule = Rule(
        rule_id="RULE-FCAU-REAL-2026-COND-1",
        source=Source(
            instrument=DOC_TITLE,
            authority=DOC_AUTHORITY,
            gazette_no=DOC_GAZETTE_NO,
            clause="Regulation 4(4)",
            page=2,
            quote_span="The importer shall maintain documentary evidence of the method of conversion/ interpretation",
        ),
        validity=Validity(
            published=PUBLICATION_DATE,
            commences=COMMENCEMENT_DATE,
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="import"),
                Condition(field="products.prepackaged", op="eq", value=True),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="documentary_compliance",
            text="Maintain interpretation evidence of coded date for Chief Food Authority inspection.",
            impact_categories=["regulatory_audit", "import_controls"],
        ),
        verification=Verification(
            status="CONDITIONAL_RULE",
            extraction_model="claude-3-5-sonnet",
            agreement=True,
        ),
    )
    # When profile conditions match:
    profile = BusinessProfile(
        business_id="BIZ-REAL-006",
        activity="import",
        products=[Product(category="beverages", prepackaged=True)],
    )
    result = evaluate_rule(rule=conditional_rule, profile=profile, as_at_date="2026-07-15")
    assert result.status == OutcomeStatus.CONDITIONAL_RULE
    assert result.missing_fields == []
    assert "external administrative/conditional compliance" in result.reason.lower()


def test_deterministic_evaluation_unsupported_clause():
    """Case 7: Clause marked NON_COMPILABLE / UNSUPPORTED -> UNSUPPORTED."""
    unsupported_rule = Rule(
        rule_id="RULE-FCAU-REAL-2026-UNSUPP",
        source=Source(
            instrument=DOC_TITLE,
            authority=DOC_AUTHORITY,
            gazette_no=DOC_GAZETTE_NO,
            clause="Regulation 12",
            page=15,
            quote_span="Discretionary guidelines as issued from time to time",
        ),
        validity=Validity(
            published=PUBLICATION_DATE,
            commences=COMMENCEMENT_DATE,
        ),
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(
            type="discretionary",
            text="Discretionary guideline",
            impact_categories=["general"],
        ),
        verification=Verification(
            status="NON_COMPILABLE",
            extraction_model="claude-3-5-sonnet",
            agreement=False,
        ),
    )
    profile = BusinessProfile(business_id="BIZ-REAL-007")
    result = evaluate_rule(rule=unsupported_rule, profile=profile, as_at_date="2026-07-15")
    assert result.status == OutcomeStatus.UNSUPPORTED
    assert "no deterministic rule exists" in result.reason.lower()


# ===========================================================================
# 6. Version Preservation During Rule Amendments
# ===========================================================================

def test_version_preservation_on_amendment(test_db):
    """Acceptance Test 6: Amending a rule preserves prior version in audit history without clobbering."""
    doc_orm = SourceDocumentORM(
        id="doc_ver_test",
        title=DOC_TITLE,
        authority=DOC_AUTHORITY,
        instrument_type="regulation",
        file_path=str(REAL_PDF_PATH),
        file_size_bytes=len(REAL_PDF_PATH.read_bytes()),
        sha256_hash="test_version_hash_" + "0" * 46,
        page_count=1,
        extraction_status="SUCCESS",
    )
    clause_orm = ClauseORM(
        clause_id="CLAUSE-VER-01",
        version_number=1,
        document_id="doc_ver_test",
        clause_number="Reg 2",
        text=VERBATIM_QUOTE_SPAN,
        start_page=1,
        end_page=1,
    )
    original_applies_if = {"all": [{"field": "activity", "op": "eq", "value": "food_manufacturing"}]}
    rule_orm = RuleORM(
        rule_id="RULE-VER-001",
        clause_id="CLAUSE-VER-01",
        clause_version=1,
        outcome_type="STANDARD",
        applies_if=original_applies_if,
        obligation={"type": "labelling", "text": "Original text", "impact_categories": []},
        validity={"published": PUBLICATION_DATE, "commences": COMMENCEMENT_DATE},
        source={
            "clause": "Reg 2",
            "instrument": DOC_TITLE,
            "authority": DOC_AUTHORITY,
            "gazette_no": DOC_GAZETTE_NO,
            "page": 1,
            "quote_span": VERBATIM_QUOTE_SPAN,
        },
        review_status="PENDING_REVIEW",
    )
    test_db.add(doc_orm)
    test_db.commit()
    test_db.add(clause_orm)
    test_db.commit()
    test_db.add(rule_orm)
    test_db.commit()

    # Apply amendment via ReviewService
    review_svc = ReviewService(test_db)
    amended_applies_if = {
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
        rationale="Added prepackaged food requirement to scope per second sentence of Regulation 2.",
        amendments={"applies_if": amended_applies_if},
    )

    test_db.refresh(rule_orm)
    # The active rule now has the updated logic:
    assert rule_orm.applies_if == amended_applies_if
    # The prior state is preserved in verification_report.version_history:
    v_rep = rule_orm.verification_report
    assert v_rep is not None
    assert "version_history" in v_rep
    assert len(v_rep["version_history"]) == 1
    hist_entry = v_rep["version_history"][0]
    assert hist_entry["amended_by"] == "lead_researcher_01"
    assert hist_entry["prior_state"]["applies_if"] == original_applies_if
