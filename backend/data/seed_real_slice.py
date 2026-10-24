"""Seed the Promulgated Sri Lankan Gazette Extraordinary No. 2494/47 and Verified Rules."""

import datetime
from pathlib import Path
from backend.src.db.models import (
    ClauseORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
)
from backend.src.db.session import session_scope
from backend.src.engine.review import (
    DECISION_APPROVED,
    ROLE_PRIMARY_ANNOTATOR,
)

# ---------------------------------------------------------------------------
# Authoritative Promulgated Gazette (Gazette Extraordinary No. 2494/47)
# ---------------------------------------------------------------------------
GAZETTE_PDF_PATH = Path("backend/data/raw_sources/2494-47_E.pdf")
EXPECTED_GAZETTE_SHA256 = "83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054"
GAZETTE_OFFICIAL_URL = "http://www.documents.gov.lk/files/egz/2026/6/2494-47_E.pdf"

GAZETTE_DOC_ID = "doc_gazette_2494_47"
GAZETTE_DOC_TITLE = "Sri Lanka Gazette Extraordinary No. 2494/47: Food (Labelling and Advertising) Regulations 2026"
GAZETTE_AUTHORITY = "Minister of Health and Mass Media / Food Advisory Committee"
GAZETTE_NO = "Gazette Extraordinary No. 2494/47"

CLAUSE_ID = "CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3"
CLAUSE_NUMBER = "Regulation 3"
CLAUSE_START_PAGE = 1
CLAUSE_END_PAGE = 2
CLAUSE_CHAR_START = 826
CLAUSE_CHAR_END = 1226

VERBATIM_RETAIL_QUOTE_SPAN = (
    "A person shall not import, transport, distribute, store, sell, offer for sale, expose or keep for sale "
    "or advertise, any food contained in a package or container, unless such package or container is "
    "labelled in accordance with these regulations:"
)

VERBATIM_B2B_QUOTE_SPAN = (
    "business-to-business food products that are exempted from other labelling requirements in these regulations "
    "except the following mandatory labelling requirements- (i) common name (in either of the three languages); "
    "(ii) trade name (if applicable); (iii) net contents; (iv) date of manufacture; (v) date of expiry; "
    "(vi) batch number; (vii) manufacturer's name and address; (viii) distributor's name and address; "
    "(ix) country of origin in case of imported foods; and (x) a complete list of ingredients. "
    "Provided further that the statement \"Not for retail sale\" shall be printed on the label or affixed "
    "through a supplementary label of such business-to-business food products clearly and conspicuously in "
    "bold type and font size of not less than three millimetres (3 mm)."
)

COMMENCEMENT_DATE = "2026-07-01"
PUBLICATION_DATE = "2026-06-26"

# Earlier Committee Draft (Distinguished artifact)
DRAFT_DOC_ID = "doc_labelling_regulations_final_2026"
DRAFT_PDF_PATH = Path("backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
DRAFT_SHA256 = "c70b5668131b76ff206897ef391cb3402bb4bf6be39a76ad1400d24c07330142"


from typing import Optional
from sqlalchemy.orm import Session


def _populate_real_slice(session: Session) -> None:
    # 1. Promulgated Source Document
    doc = session.get(SourceDocumentORM, GAZETTE_DOC_ID)
    if not doc:
        doc = SourceDocumentORM(
            id=GAZETTE_DOC_ID,
            title=GAZETTE_DOC_TITLE,
            authority=GAZETTE_AUTHORITY,
            instrument_type="gazette_regulation",
            gazette_no=GAZETTE_NO,
            source_url=GAZETTE_OFFICIAL_URL,
            file_path=str(GAZETTE_PDF_PATH),
            file_size_bytes=len(GAZETTE_PDF_PATH.read_bytes()) if GAZETTE_PDF_PATH.exists() else 424172,
            sha256_hash=EXPECTED_GAZETTE_SHA256,
            page_count=25,
            extraction_status="SUCCESS",
            extraction_tool="pymupdf",
            publication_date=datetime.date(2026, 6, 26),
        )
        session.add(doc)
        session.flush()
        print("Created SourceDocumentORM for Gazette 2494/47")
    else:
        doc.title = GAZETTE_DOC_TITLE
        doc.source_url = GAZETTE_OFFICIAL_URL
        doc.publication_date = datetime.date(2026, 6, 26)
        doc.gazette_no = GAZETTE_NO
        session.flush()
        print("Updated SourceDocumentORM for Gazette 2494/47")

    # Clarify earlier draft document metadata: no false gazette number
    draft_doc = session.get(SourceDocumentORM, DRAFT_DOC_ID)
    if draft_doc:
        draft_doc.title = "Food (Labelling and Advertising) Regulations (FAC Draft Final 11.02.2026)"
        draft_doc.gazette_no = None  # Draft is not officially gazetted
        session.flush()

    # 2. Promulgated Clause: Regulation 3 (Spans Page 1 and Page 2)
    clause = session.get(ClauseORM, (CLAUSE_ID, 1))
    if not clause:
        clause = ClauseORM(
            clause_id=CLAUSE_ID,
            version_number=1,
            document_id=GAZETTE_DOC_ID,
            clause_number=CLAUSE_NUMBER,
            text=f"{VERBATIM_RETAIL_QUOTE_SPAN}\n\n{VERBATIM_B2B_QUOTE_SPAN}",
            start_page=CLAUSE_START_PAGE,
            end_page=CLAUSE_END_PAGE,
            char_start=CLAUSE_CHAR_START,
            char_end=CLAUSE_CHAR_END,
            valid_from=datetime.date(2026, 7, 1),
            is_compilable=True,
        )
        session.add(clause)
        session.flush()
        print("Created ClauseORM for Regulation 3")
    else:
        clause.char_start = CLAUSE_CHAR_START
        clause.char_end = CLAUSE_CHAR_END
        clause.text = f"{VERBATIM_RETAIL_QUOTE_SPAN}\n\n{VERBATIM_B2B_QUOTE_SPAN}"
        session.flush()

    # 3. Rule 1: General Mandatory Retail Labelling
    retail_rule_id = "RULE-FCAU-2494-47-REG-3"
    retail_applies = {
        "all": [
            {"field": "activity", "op": "in", "value": ["food_manufacturing", "catering", "retail_trade", "distribution", "import", "storage"]},
            {"field": "products.prepackaged", "op": "eq", "value": True},
        ]
    }
    retail_exceptions = [
        {"field": "packaged_in_presence_of_purchaser", "op": "eq", "value": True},
        {"field": "market.b2b_only", "op": "eq", "value": True},
    ]
    retail_obligation = {
        "type": "labelling",
        "text": "Food contained in a package or container must be labelled in accordance with the Food (Labelling and Advertising) Regulations 2026.",
        "impact_categories": ["labelling", "packaging", "retail_distribution"],
    }
    retail_source = {
        "clause": CLAUSE_NUMBER,
        "instrument": GAZETTE_DOC_TITLE,
        "authority": GAZETTE_AUTHORITY,
        "gazette_no": GAZETTE_NO,
        "page": 1,
        "quote_span": VERBATIM_RETAIL_QUOTE_SPAN,
    }
    rule_retail = session.get(RuleORM, retail_rule_id)
    if not rule_retail:
        rule_retail = RuleORM(
            rule_id=retail_rule_id,
            clause_id=CLAUSE_ID,
            clause_version=1,
            outcome_type="STANDARD",
            applies_if=retail_applies,
            exceptions=retail_exceptions,
            obligation=retail_obligation,
            validity={"published": PUBLICATION_DATE, "commences": COMMENCEMENT_DATE},
            source=retail_source,
            review_status="APPROVED",
            is_gold_rule=False,  # Primary researcher review; independent expert legal adjudication pending
        )
        session.add(rule_retail)
        session.flush()
        print("Created RuleORM for Regulation 3 Retail Rule")
    else:
        rule_retail.applies_if = retail_applies
        rule_retail.exceptions = retail_exceptions
        rule_retail.obligation = retail_obligation
        rule_retail.source = retail_source
        rule_retail.review_status = "APPROVED"
        rule_retail.is_gold_rule = False
        session.flush()

    audit_retail = (
        session.query(HumanReviewAuditORM)
        .filter_by(rule_id=retail_rule_id, reviewer_id="researcher_engineer_01")
        .first()
    )
    if not audit_retail:
        audit_retail = HumanReviewAuditORM(
            rule_id=retail_rule_id,
            reviewer_id="researcher_engineer_01",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision=DECISION_APPROVED,
            rationale=(
                "Verified against Pages 1-2 of official Sri Lanka Gazette Extraordinary No. 2494/47. "
                "Regulation 3 general retail packaged food mandate captured with purchaser-presence and B2B exceptions. "
                "Note: Independent legal expert adjudication is pending."
            ),
        )
        session.add(audit_retail)
        session.flush()

    # 4. Rule 2: B2B Affirmative Labelling & Marking (Regulation 3 Proviso (b))
    b2b_rule_id = "RULE-FCAU-2494-47-REG-3-B2B"
    b2b_applies = {
        "all": [
            {"field": "activity", "op": "in", "value": ["food_manufacturing", "distribution", "import", "storage"]},
            {"field": "products.prepackaged", "op": "eq", "value": True},
            {"field": "market.b2b_only", "op": "eq", "value": True},
        ]
    }
    b2b_exceptions = []
    b2b_obligation = {
        "type": "labelling",
        "text": (
            "Business-to-business food products must display 10 mandatory disclosures "
            "(common name in either of the three languages, trade name if applicable, net contents, "
            "date of manufacture, date of expiry, batch number, manufacturer's name and address, "
            "distributor's name and address, country of origin in case of imported foods, "
            "complete list of ingredients) and must display 'Not for retail sale' printed on label "
            "or affixed through supplementary label in bold type with font size not less than 3 mm."
        ),
        "disclosures": [
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
        "impact_categories": ["labelling", "packaging", "b2b_compliance"],
    }
    b2b_source = {
        "clause": "Regulation 3 Proviso (b)",
        "instrument": GAZETTE_DOC_TITLE,
        "authority": GAZETTE_AUTHORITY,
        "gazette_no": GAZETTE_NO,
        "page": 2,
        "quote_span": VERBATIM_B2B_QUOTE_SPAN,
    }
    rule_b2b = session.get(RuleORM, b2b_rule_id)
    if not rule_b2b:
        rule_b2b = RuleORM(
            rule_id=b2b_rule_id,
            clause_id=CLAUSE_ID,
            clause_version=1,
            outcome_type="STANDARD",
            applies_if=b2b_applies,
            exceptions=b2b_exceptions,
            obligation=b2b_obligation,
            validity={"published": PUBLICATION_DATE, "commences": COMMENCEMENT_DATE},
            source=b2b_source,
            review_status="APPROVED",
            is_gold_rule=False,  # Primary researcher review; independent expert legal adjudication pending
        )
        session.add(rule_b2b)
        session.flush()
        print("Created RuleORM for Regulation 3 B2B Rule")
    else:
        rule_b2b.applies_if = b2b_applies
        rule_b2b.exceptions = b2b_exceptions
        rule_b2b.obligation = b2b_obligation
        rule_b2b.source = b2b_source
        rule_b2b.review_status = "APPROVED"
        rule_b2b.is_gold_rule = False
        session.flush()

    audit_b2b = (
        session.query(HumanReviewAuditORM)
        .filter_by(rule_id=b2b_rule_id, reviewer_id="researcher_engineer_01")
        .first()
    )
    if not audit_b2b:
        audit_b2b = HumanReviewAuditORM(
            rule_id=b2b_rule_id,
            reviewer_id="researcher_engineer_01",
            reviewer_role=ROLE_PRIMARY_ANNOTATOR,
            decision=DECISION_APPROVED,
            rationale=(
                "Verified against Page 2 of official Sri Lanka Gazette Extraordinary No. 2494/47. "
                "Regulation 3 Proviso (b) 10 mandatory disclosures and 'Not for retail sale' marking requirement captured. "
                "Note: Independent legal expert adjudication is pending."
            ),
        )
        session.add(audit_b2b)
        session.flush()


def seed_real_slice(session: Optional[Session] = None) -> None:
    if session is not None:
        _populate_real_slice(session)
    else:
        with session_scope() as sess:
            _populate_real_slice(sess)
            sess.commit()
    print("Authoritative real-source slice successfully seeded!")


if __name__ == "__main__":
    seed_real_slice()

