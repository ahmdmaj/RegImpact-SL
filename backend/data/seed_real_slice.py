"""Seed the First Verified Real-Source Vertical Slice into PostgreSQL database."""

import datetime
from pathlib import Path
from backend.src.db.models import (
    ClauseORM,
    DocumentPageORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
)
from backend.src.db.session import session_scope
from backend.src.engine.review import (
    DECISION_APPROVED,
    ROLE_PRIMARY_ANNOTATOR,
)

REAL_PDF_PATH = Path("backend/data/raw_sources/Labelling_Regulations_Final_-_11.02.2026.pdf")
EXPECTED_SHA256 = "c70b5668131b76ff206897ef391cb3402bb4bf6be39a76ad1400d24c07330142"

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


def seed_real_slice():
    with session_scope() as session:
        # 1. Source Document
        doc = session.get(SourceDocumentORM, DOC_ID)
        if not doc:
            doc = SourceDocumentORM(
                id=DOC_ID,
                title=DOC_TITLE,
                authority=DOC_AUTHORITY,
                instrument_type="regulation",
                gazette_no=DOC_GAZETTE_NO,
                file_path=str(REAL_PDF_PATH),
                file_size_bytes=len(REAL_PDF_PATH.read_bytes()),
                sha256_hash=EXPECTED_SHA256,
                page_count=22,
                extraction_status="SUCCESS",
                extraction_tool="pymupdf",
                publication_date=datetime.date(2026, 7, 1),
            )
            session.add(doc)
            session.flush()
            print("Created SourceDocumentORM")
        else:
            doc.publication_date = datetime.date(2026, 7, 1)
            doc.gazette_no = DOC_GAZETTE_NO
            doc.authority = DOC_AUTHORITY
            session.flush()
            print("Updated SourceDocumentORM metadata")

        # 2. Clause
        clause = session.get(ClauseORM, (CLAUSE_ID, 1))
        if not clause:
            clause = ClauseORM(
                clause_id=CLAUSE_ID,
                version_number=1,
                document_id=DOC_ID,
                clause_number=CLAUSE_NUMBER,
                text=VERBATIM_QUOTE_SPAN,
                start_page=CLAUSE_PAGE,
                end_page=CLAUSE_PAGE,
                char_start=CLAUSE_CHAR_START,
                char_end=CLAUSE_CHAR_END,
                valid_from=datetime.date(2026, 7, 1),
                is_compilable=True,
            )
            session.add(clause)
            session.flush()
            print("Created ClauseORM")
        else:
            clause.char_start = CLAUSE_CHAR_START
            clause.char_end = CLAUSE_CHAR_END
            session.flush()
            print("ClauseORM already exists, updated offsets")

        # 3. Rule
        rule = session.get(RuleORM, "RULE-FCAU-REAL-2026-REG-2")
        if not rule:
            rule = RuleORM(
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
                review_status="APPROVED",
                is_gold_rule=False,  # Primary annotator review; not gold expert adjudication
            )
            session.add(rule)
            session.flush()
            print("Created RuleORM")

            # Audit record
            audit = HumanReviewAuditORM(
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
            session.add(audit)
            session.flush()
            print("Recorded HumanReviewAuditORM")
        else:
            print("RuleORM already exists")

        session.commit()
        print("Real-source slice seeded successfully in PostgreSQL!")


if __name__ == "__main__":
    seed_real_slice()
