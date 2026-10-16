"""Script: Seed Regulatory Corpus (Dataset A).

Generates realistic structural PDF fixtures representing Sri Lankan gazettes
and regulations, ingests them via DocumentIngestionService into the database,
segments clauses, computes embeddings, and registers approved rules.

NOTE: These documents and clauses are structural test fixtures with realistic
statutory thresholds (e.g., 50 kg/day, 10 m3/day) awaiting final expert-reviewed
replacement with official gazette PDFs.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pymupdf
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, DocumentPageORM, RuleORM, SourceDocumentORM
from backend.src.db.session import init_db, session_scope
from backend.src.extraction.embedding_client import MockEmbeddingClient
from backend.src.extraction.ingestion import (
    DocumentIngestionService,
    segment_clauses_from_page,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_SOURCES_DIR = Path("backend/data/raw_sources")


# ---------------------------------------------------------------------------
# Document Fixture Definitions
# ---------------------------------------------------------------------------

DOCUMENT_FIXTURES: List[Dict[str, Any]] = [
    {
        "doc_id": "doc_fcau_labelling_2024",
        "filename": "doc_fcau_labelling_2024.pdf",
        "title": "Food (Labelling and Advertising) Regulations 2024",
        "authority": "Food Control Administration Unit (FCAU)",
        "instrument_type": "regulation",
        "gazette_no": "Gazette Extraordinary No. 2380/14",
        "publication_date": "2024-01-15",
        "commencement_date": "2024-06-01",
        "source_url": None,  # Null per constraint: no hallucinated URLs
        "pages": [
            (
                "THE FOOD ACT, No. 26 OF 1980\n"
                "Regulations made by the Minister of Health under Section 32 of the Food Act, No. 26 of 1980.\n\n"
                "PART I - GENERAL LABELLING REQUIREMENTS\n\n"
                "Regulation 4. Every food manufacturing enterprise having a production capacity of 50 kg per day "
                "or more shall ensure that each retail package carries a nutrition information panel displaying energy, "
                "protein, carbohydrate, and fat content.\n\n"
                "Regulation 5. The information required to be displayed on a package shall be printed in letters of "
                "not less than 1.5 millimetres in height and clearly legible against a contrasting background."
            ),
            (
                "PART II - SPECIAL PROVISIONS AND MINISTERIAL APPROVALS\n\n"
                "Regulation 9. Novel food ingredients shall obtain prior ministerial approval before import, "
                "commercial distribution, or retail sale in Sri Lanka.\n\n"
                "Regulation 15. Every manufacturer or packager of food products containing synthetic food colorings "
                "shall declare the common chemical name and international numbering system code on the principal display panel."
            ),
        ],
        "rules": [
            {
                "rule_id": "RULE-FCAU-REG-4",
                "clause_number": "Regulation 4",
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "production_capacity.kg_per_day", "op": "gte", "value": 50},
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "labelling",
                    "text": "Display nutrition information panel",
                    "impact_categories": ["labelling", "packaging"],
                },
                "validity": {"published": "2024-01-15", "commences": "2024-06-01"},
                "source": {
                    "clause": "Regulation 4",
                    "instrument": "Food (Labelling and Advertising) Regulations 2024",
                    "quote_span": "production capacity of 50 kg per day or more shall ensure that each retail package carries a nutrition information panel",
                },
                "review_status": "APPROVED",
            },
            {
                "rule_id": "RULE-FCAU-REG-15",
                "clause_number": "Regulation 15",
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "uses_synthetic_colorings", "op": "eq", "value": True},
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "labelling",
                    "text": "Declare chemical name and INS code for synthetic colorings",
                    "impact_categories": ["labelling"],
                },
                "validity": {"published": "2024-01-15", "commences": "2024-06-01"},
                "source": {
                    "clause": "Regulation 15",
                    "instrument": "Food (Labelling and Advertising) Regulations 2024",
                    "quote_span": "containing synthetic food colorings shall declare the common chemical name and international numbering system code",
                },
                "review_status": "APPROVED",
            },
            # Note: Regulation 9 is intentionally omitted from rules to represent a verified COVERAGE GAP
        ],
    },
    {
        "doc_id": "doc_cea_epl_2022",
        "filename": "doc_cea_epl_2022.pdf",
        "title": "National Environmental (Protection and Quality) Regulations (EPL Standards) 2022",
        "authority": "Central Environmental Authority (CEA)",
        "instrument_type": "regulation",
        "gazette_no": "Gazette Extraordinary No. 2265/30",
        "publication_date": "2022-02-01",
        "commencement_date": "2022-05-01",
        "source_url": None,
        "pages": [
            (
                "NATIONAL ENVIRONMENTAL ACT, No. 47 OF 1980\n"
                "Regulations made by the Minister of Environment under Section 32 of the National Environmental Act, No. 47 of 1980.\n\n"
                "PART I - PRESCRIBED ACTIVITIES AND ENVIRONMENTAL PROTECTION LICENSES\n\n"
                "Regulation 3. An industrial activity categorized under Part A having wastewater discharge exceeding "
                "10 cubic meters per day shall obtain an Environmental Protection License (EPL) prior to commencement of operations.\n\n"
                "Regulation 8. Storage of hazardous industrial chemicals exceeding 500 liters shall be equipped with "
                "secondary containment bunding capable of holding 110 percent of the largest container capacity."
            ),
        ],
        "rules": [
            {
                "rule_id": "RULE-CEA-REG-3",
                "clause_number": "Regulation 3",
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "industry_category", "op": "eq", "value": "Part A"},
                        {"field": "wastewater_discharge_m3_per_day", "op": "gt", "value": 10},
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "licensing",
                    "text": "Obtain Environmental Protection License (EPL)",
                    "impact_categories": ["licensing", "operational_compliance"],
                },
                "validity": {"published": "2022-02-01", "commences": "2022-05-01"},
                "source": {
                    "clause": "Regulation 3",
                    "instrument": "National Environmental (Protection and Quality) Regulations 2022",
                    "quote_span": "categorized under Part A having wastewater discharge exceeding 10 cubic meters per day shall obtain an Environmental Protection License",
                },
                "review_status": "APPROVED",
            },
            {
                "rule_id": "RULE-CEA-REG-8",
                "clause_number": "Regulation 8",
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "hazardous_chemicals_storage_liters", "op": "gt", "value": 500},
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "safety",
                    "text": "Construct secondary containment bunding for hazardous chemicals",
                    "impact_categories": ["facility_safety", "capital_expenditure"],
                },
                "validity": {"published": "2022-02-01", "commences": "2022-05-01"},
                "source": {
                    "clause": "Regulation 8",
                    "instrument": "National Environmental (Protection and Quality) Regulations 2022",
                    "quote_span": "Storage of hazardous industrial chemicals exceeding 500 liters shall be equipped with secondary containment bunding",
                },
                "review_status": "APPROVED",
            },
        ],
    },
    {
        "doc_id": "doc_caa_mrp_2023",
        "filename": "doc_caa_mrp_2023.pdf",
        "title": "Consumer Affairs Authority (Display of Maximum Retail Prices) Direction 2023",
        "authority": "Consumer Affairs Authority (CAA)",
        "instrument_type": "direction",
        "gazette_no": "Gazette Extraordinary No. 2314/05",
        "publication_date": "2023-01-10",
        "commencement_date": "2023-03-01",
        "source_url": None,
        "pages": [
            (
                "CONSUMER AFFAIRS AUTHORITY ACT, No. 09 OF 2003\n"
                "Direction under Section 10(1) of the Consumer Affairs Authority Act, No. 09 of 2003.\n\n"
                "PART I - CONSUMER GOODS PRICING & TRANSCRIPTION\n\n"
                "Section 10. Every distributor or retailer trading in essential consumer commodities shall conspicuously "
                "display the Maximum Retail Price (MRP) at the point of sale in Sinhala, Tamil, and English.\n\n"
                "Section 14. Retailers possessing an annual turnover exceeding 10 million LKR shall maintain automated "
                "digital point of sale receipt records for all consumer transactions."
            ),
        ],
        "rules": [
            {
                "rule_id": "RULE-CAA-SEC-10",
                "clause_number": "Section 10",
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "retail_trade"},
                        {"field": "trades_essential_commodities", "op": "eq", "value": True},
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "pricing",
                    "text": "Conspicuously display Maximum Retail Price (MRP)",
                    "impact_categories": ["consumer_transparency", "point_of_sale"],
                },
                "validity": {"published": "2023-01-10", "commences": "2023-03-01"},
                "source": {
                    "clause": "Section 10",
                    "instrument": "Consumer Affairs Authority (Display of Maximum Retail Prices) Direction 2023",
                    "quote_span": "trading in essential consumer commodities shall conspicuously display the Maximum Retail Price (MRP)",
                },
                "review_status": "APPROVED",
            },
            {
                "rule_id": "RULE-CAA-SEC-14",
                "clause_number": "Section 14",
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "retail_trade"},
                        {"field": "annual_turnover_lkr", "op": "gt", "value": 10000000},
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "recordkeeping",
                    "text": "Maintain automated digital point of sale receipt records",
                    "impact_categories": ["recordkeeping", "it_systems"],
                },
                "validity": {"published": "2023-01-10", "commences": "2023-03-01"},
                "source": {
                    "clause": "Section 14",
                    "instrument": "Consumer Affairs Authority (Display of Maximum Retail Prices) Direction 2023",
                    "quote_span": "annual turnover exceeding 10 million LKR shall maintain automated digital point of sale receipt records",
                },
                "review_status": "APPROVED",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# PDF Generation Helper
# ---------------------------------------------------------------------------

def generate_pdf_fixtures(target_dir: Path, force: bool = False) -> List[Path]:
    """Generate structural test PDF fixtures using PyMuPDF."""
    target_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: List[Path] = []

    for fixture in DOCUMENT_FIXTURES:
        pdf_path = target_dir / fixture["filename"]
        if pdf_path.exists() and not force:
            logger.info("PDF fixture exists: %s", pdf_path)
            generated_paths.append(pdf_path)
            continue

        doc = pymupdf.open()
        for page_text in fixture["pages"]:
            page = doc.new_page(width=595, height=842)  # A4 size in points
            rect = pymupdf.Rect(50, 50, 545, 792)
            page.insert_textbox(rect, page_text, fontsize=10, fontname="helv")

        doc.save(str(pdf_path))
        doc.close()
        logger.info("Generated PDF fixture: %s (%d pages)", pdf_path, len(fixture["pages"]))
        generated_paths.append(pdf_path)

    return generated_paths


# ---------------------------------------------------------------------------
# Corpus Seeder Service
# ---------------------------------------------------------------------------

def seed_regulatory_corpus(
    db: Session,
    raw_dir: Optional[Path] = None,
    force: bool = False,
    embedding_dimension: int = 64,
) -> Dict[str, Any]:
    """Seed the database with official source documents, segmented clauses, and rules.

    Returns:
        Summary dict containing counts of ingested documents, clauses, and rules.
    """
    raw_path = raw_dir or RAW_SOURCES_DIR
    generate_pdf_fixtures(raw_path, force=force)

    ingestion_service = DocumentIngestionService(pdf_store_dir=raw_path)
    embedding_client = MockEmbeddingClient(dimension=embedding_dimension)

    docs_ingested = 0
    clauses_created = 0
    rules_registered = 0

    for fixture in DOCUMENT_FIXTURES:
        doc_id = fixture["doc_id"]
        pdf_file = raw_path / fixture["filename"]

        # Check existing document
        existing_doc = db.get(SourceDocumentORM, doc_id)
        if existing_doc and not force:
            logger.info("Document %r already ingested. Skipping ingestion.", doc_id)
        else:
            if existing_doc and force:
                logger.info("Force flag set; removing existing document %r.", doc_id)
                db.delete(existing_doc)
                db.flush()

            result = ingestion_service.ingest(
                db=db,
                pdf_path=pdf_file,
                doc_id=doc_id,
                title=fixture["title"],
                authority=fixture["authority"],
                instrument_type=fixture["instrument_type"],
                gazette_no=fixture["gazette_no"],
                source_url=fixture["source_url"],
                publication_date=fixture["publication_date"],
            )
            if not result.success:
                logger.error("Failed to ingest %s: %s", doc_id, result.error)
                continue
            docs_ingested += 1

        # Fetch pages to segment clauses
        pages = (
            db.query(DocumentPageORM)
            .filter_by(document_id=doc_id)
            .order_by(DocumentPageORM.page_number)
            .all()
        )

        for page in pages:
            segmented = segment_clauses_from_page(page.raw_text, page.page_number)
            for seg in segmented:
                clause_pk = f"CLAUSE-{doc_id.upper()}-{seg.clause_number.replace(' ', '-').upper()}"
                existing_clause = db.query(ClauseORM).filter_by(clause_id=clause_pk).first()

                if not existing_clause:
                    emb = embedding_client.embed_text(seg.text)
                    is_compilable = any(
                        r["clause_number"] == seg.clause_number for r in fixture.get("rules", [])
                    )
                    clause_orm = ClauseORM(
                        clause_id=clause_pk,
                        version_number=1,
                        document_id=doc_id,
                        clause_number=seg.clause_number,
                        text=seg.text,
                        start_page=seg.start_page,
                        end_page=seg.end_page,
                        char_start=seg.char_start,
                        char_end=seg.char_end,
                        is_compilable=is_compilable,
                        embedding=emb,
                    )
                    db.add(clause_orm)
                    db.flush()
                    clauses_created += 1

        # Register verified rules
        for r_spec in fixture.get("rules", []):
            rule_pk = r_spec["rule_id"]
            existing_rule = db.query(RuleORM).filter_by(rule_id=rule_pk).first()
            if not existing_rule:
                target_clause_pk = f"CLAUSE-{doc_id.upper()}-{r_spec['clause_number'].replace(' ', '-').upper()}"
                rule_orm = RuleORM(
                    rule_id=rule_pk,
                    clause_id=target_clause_pk,
                    clause_version=1,
                    outcome_type=r_spec["outcome_type"],
                    applies_if=r_spec["applies_if"],
                    exceptions=r_spec.get("exceptions", []),
                    obligation=r_spec["obligation"],
                    validity=r_spec["validity"],
                    source=r_spec["source"],
                    review_status=r_spec.get("review_status", "APPROVED"),
                )
                db.add(rule_orm)
                db.flush()
                rules_registered += 1

    db.commit()
    summary = {
        "documents_ingested": docs_ingested,
        "clauses_created": clauses_created,
        "rules_registered": rules_registered,
        "raw_dir": str(raw_path),
    }
    logger.info("Corpus seeding completed successfully: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Dataset A (Regulatory Corpus) into RegImpact-SL database.")
    parser.add_argument("--raw-dir", type=str, default="backend/data/raw_sources", help="Directory for raw PDFs")
    parser.add_argument("--db-url", type=str, default=None, help="Database URL (default: DATABASE_URL env or SQLite)")
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing documents and PDFs")
    args = parser.parse_args()

    engine = init_db(args.db_url)
    with session_scope(engine=engine) as session:
        summary = seed_regulatory_corpus(
            db=session,
            raw_dir=Path(args.raw_dir),
            force=args.force,
        )
        print("\n--- Seeding Summary ---")
        for k, v in summary.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
