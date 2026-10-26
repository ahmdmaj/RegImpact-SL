"""Phase 3.8: Source Verification & Bounded Rule Consistency Suite.

Validates the source grounding, exact quotation spans, and statutory boundaries
for the three audited rules across authentic Gazette PDFs:
  1. Gazette 1795/51 Regulation 7(ii) - Infant flavour enhancer prohibition.
  2. Gazette 1795/51 Regulation 8(2)(d) - Flavour enhancer label declaration.
  3. Gazette 2113/16 Schedule II Item 3.1(h) vs 3.1(i) - Jam preservative limits.
"""

from pathlib import Path
import fitz
import pytest
from sqlalchemy import text

from backend.src.db.models import ClauseORM, RuleORM
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.verifier import RuleVerifier
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

PDF_FLAVOURING = Path("backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf")
PDF_PRESERVATIVE = Path("backend/data/raw_sources/preservative-english.pdf")

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
# 1. Gazette 1795/51 Regulation 7(ii) - Infant Prohibition Verification
# ---------------------------------------------------------------------------

def test_gazette_1795_51_regulation_7_ii_verbatim_text():
    """Verify exact text, page location, and definition context of Regulation 7(ii)."""
    assert PDF_FLAVOURING.exists(), f"Source PDF missing: {PDF_FLAVOURING}"
    doc = fitz.open(PDF_FLAVOURING)
    
    # Page 2 (0-indexed page 1) contains Regulation 7
    page_2_text = doc[1].get_text()
    assert "7. Flavour enhancers" in page_2_text or "7.\nFlavour enhancers" in page_2_text
    
    # Verify subclause (i) vs (ii) vs (iii)
    assert "(i) may be added to foods subject to observance of Good Manufacturing Practices" in page_2_text
    exact_infant_text = "(ii) shall not be added to any food for infants or young children below three years of age; and"
    assert exact_infant_text in page_2_text, "Regulation 7(ii) verbatim text not found on Page 2"
    assert "(iii) shall not be used in the foods specified in Schedule III hereto." in page_2_text
    
    # Page 3 contains definition of foods for infants
    page_3_text = doc[2].get_text()
    assert "foods  for infants or young children below three years of age" in page_3_text
    assert "means foods that are specifically prepared" in page_3_text
    assert "manufactured or marketed for infants or young children below three years of age." in page_3_text


def test_rule_flavour_infant_prohibition_verifier(live_db):
    """Verify RULE-FLAVOUR-INFANT-PROHIBITION against live database and page text."""
    r_orm = live_db.get(RuleORM, "RULE-FLAVOUR-INFANT-PROHIBITION")
    assert r_orm is not None, "RULE-FLAVOUR-INFANT-PROHIBITION not found in DB"
    assert r_orm.review_status == "PENDING_REVIEW"
    assert r_orm.is_gold_rule is False
    
    # Source quote span in DB must be exact Regulation 7(ii)
    expected_quote = "(ii) shall not be added to any food for infants or young children below three years of age; and"
    assert r_orm.source["quote_span"] == expected_quote
    assert r_orm.source["page"] == 2
    
    # Verification against clause text
    c_orm = live_db.get(ClauseORM, (r_orm.clause_id, 1))
    assert c_orm is not None
    assert expected_quote in c_orm.text
    
    verifier = RuleVerifier()
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
        source_text=c_orm.text,
        metadata={"published": r_orm.validity["published"], "commences": r_orm.validity["commences"]},
    )
    assert rep.is_valid is True, f"Verifier failed: {rep.issues}"


# ---------------------------------------------------------------------------
# 2. Gazette 1795/51 Regulation 8(2)(d) - Flavour Label Declaration Verification
# ---------------------------------------------------------------------------

def test_gazette_1795_51_regulation_8_2_d_verbatim_text():
    """Verify exact text and page location of Regulation 8(2)(d)."""
    assert PDF_FLAVOURING.exists(), f"Source PDF missing: {PDF_FLAVOURING}"
    doc = fitz.open(PDF_FLAVOURING)
    
    page_2_text = doc[1].get_text()
    assert "8." in page_2_text
    assert "(2) The label printed on or attached to the package of food containing" in page_2_text
    
    # Verify subclause (2)(d) verbatim text
    expected_clause_d = (
        "(d) any flavour enhancer or enhancers as an ingredient, shall include the words "
        "‘‘flavour enhancer used’’ or\n‘‘flavour enhancers used’’ as the case may be, "
        "along with the common name or names and the INS\nnumber or numbers, as the case may be."
    )
    # Check normalized text presence
    normalized_p2 = " ".join(page_2_text.split())
    normalized_d = " ".join(expected_clause_d.split())
    assert normalized_d in normalized_p2, "Regulation 8(2)(d) text not found on Page 2"


def test_rule_flavour_label_declaration_verifier(live_db):
    """Verify RULE-FLAVOUR-LABEL-DECLARATION against live database and page text."""
    r_orm = live_db.get(RuleORM, "RULE-FLAVOUR-LABEL-DECLARATION")
    assert r_orm is not None, "RULE-FLAVOUR-LABEL-DECLARATION not found in DB"
    assert r_orm.review_status == "PENDING_REVIEW"
    assert r_orm.is_gold_rule is False
    
    assert r_orm.source["page"] == 2
    assert "flavour enhancer used" in r_orm.source["quote_span"]
    
    c_orm = live_db.get(ClauseORM, (r_orm.clause_id, 1))
    assert c_orm is not None
    
    verifier = RuleVerifier()
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
        source_text=c_orm.text,
        metadata={"published": r_orm.validity["published"], "commences": r_orm.validity["commences"]},
    )
    assert rep.is_valid is True, f"Verifier failed: {rep.issues}"


# ---------------------------------------------------------------------------
# 3. Gazette 2113/16 Schedule II Items 3.1(h) vs 3.1(i) - Jam Preservatives
# ---------------------------------------------------------------------------

def test_gazette_2113_16_schedule_ii_jam_items_distinction():
    """Verify that Schedule II distinguishes standard jams (3.1(h)) from low-sugar jams (3.1(i))."""
    assert PDF_PRESERVATIVE.exists(), f"Source PDF missing: {PDF_PRESERVATIVE}"
    doc = fitz.open(PDF_PRESERVATIVE)
    
    # Page 5 (0-indexed page 4) contains Schedule II Item 3.1
    page_5_text = doc[4].get_text()
    
    # Item 3.1(h) - standard jams
    assert "(h) Jams, Jellies, marmalades" in page_5_text
    
    # Item 3.1(i) - low-sugar / sugar-free jams
    assert "(i) Jams, Jellies and marmalades," in page_5_text
    assert "low in sugar or sugar free" in page_5_text
    
    # Verify distinct Sorbates limits: 300 mg/kg vs 500 mg/kg
    lines = [l.strip() for l in page_5_text.splitlines() if l.strip()]
    
    idx_h = next(i for i, l in enumerate(lines) if "(h) Jams, Jellies, marmalades" in l)
    idx_i = next(i for i, l in enumerate(lines) if "(i) Jams, Jellies and marmalades" in l)
    assert idx_h < idx_i
    
    h_block = " ".join(lines[idx_h:idx_i])
    assert "Sorbates" in h_block and "300" in h_block
    assert "Sulphites" in h_block and "100" in h_block
    
    i_block = " ".join(lines[idx_i:idx_i+15])
    assert "Sorbates" in i_block and "500" in i_block
    assert "Sulphites" in i_block and "100" in i_block


def test_rule_preservative_jam_jelly_limit_scope(live_db):
    """Verify RULE-PRESERVATIVE-JAM-JELLY-LIMIT currently models Item 3.1(h)."""
    r_orm = live_db.get(RuleORM, "RULE-PRESERVATIVE-JAM-JELLY-LIMIT")
    assert r_orm is not None, "RULE-PRESERVATIVE-JAM-JELLY-LIMIT not found in DB"
    assert r_orm.review_status == "PENDING_REVIEW"
    assert r_orm.is_gold_rule is False
    
    # Quote span corresponds specifically to Item 3.1(h)
    assert "(h) Jams, Jellies, marmalades: Sorbates 300 mg/kg" in r_orm.source["quote_span"]
    assert r_orm.source["page"] == 5
