"""Controlled Ingestion Script for Gazette 1688/28 (Phase 4.2).

Performs:
1. Verifies physical source PDF and hash.
2. Updates SourceDocumentORM metadata for Gazette 1688/28.
3. Updates DocumentPageORM raw_text for Page 1 and Page 2.
4. Generates genuine local BGE vectors (768-dim, unit-normalized) for the 3 candidate clauses.
5. Ingests the 3 candidate clauses into ClauseORM with composite PK (clause_id, version_number).
6. Atomically commits the transaction and reads back the records to verify database state.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import math
from pathlib import Path
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, DocumentPageORM, SourceDocumentORM

from backend.src.db.session import session_scope
from backend.src.extraction.embedding_client import SentenceTransformerEmbeddingClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOC_ID = "doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7"
EXPECTED_SHA256 = "3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7"
PDF_PATH = "backend/data/raw_sources/food_amendment_colouring_substances_regulations_2011_en.pdf"

# Verified text definitions from verified_ocr_text.md
PAGE_1_TEXT = """L.D.—B.11/80.
FOOD ACT, No. 26 OF 1980
REGULATIONS made by the Minister of Health under section 32 of the Food Act, No. 26 of 1980 in consultation with the Food Advisory Committee.

Maithripala Sirisena,
Minister of Health.

Ministry of Health,
Colombo,
8th January, 2011.

Regulations
“The Food (Colouring Substances) Regulations - 2006” published in the Gazette Extraordinay, No. 1472/19 of November 23, 2006 as amended by Regulation published in the Gazette Extraordinary, No. 1585/26 of January 23, 2009 is hereby further amended as follows:-
(1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:-
“(iv) fish, molluscs, crustaceans and echinoderms;”.
(2) in Schedule I thereto, by the repeal of Table I and II of that Schedule and the substitution therefor of the following:-

“TABLE - I
Synthetic dyes that are permitted to be used as colouring substances in food
No. | Column I Colour | Column II Common Name | Column III INS Number
1 | Red | 1 Carmoisine (Azorubine) | 122
1 | Red | 2 Ponceau 4R | 124
1 | Red | 3 Erythrosine | 127
1 | Red | 4 Allura Red | 129
2 | Yellow | 1 Sunset yellow FCF | 110
2 | Yellow | 2 Tartrazine | 102
3 | Blue | 1 Indigotine | 132
3 | Blue | 2 (Indigo carmine) | 132
3 | Blue | 3 Brilliant Blue FCF | 133
4 | Green | 1 Fast Green FCF | 143"""

PAGE_2_TEXT = """TABLE - II
Other Colouring substances permitted to be used
No. | Column I Natural Colouring Substances | Column II INS Number
1 | Curcumin | 100(i)
2 | Riboflavin 5' Phosphate | 101(i)
3 | Riboflavin 5' Phosphate, sodium | 101(ii)
4 | Cochineal (Carminic acid, Carmines) | 120
5 | Chlorophylls | 140
6 | Chlorophylls Copper Complex | 141(i)
7 | Caramel Class I | 150a
8 | Caramel Class III | 150c
9 | Caramel Class IV | 150d
10 | Carotenes, Natural Extracts, (Vegetable) | 160a(ii)
11 | Annatto Extracts | 160b
12 | Paprika oleoresin (Capsanthin or Capsorubin) | 160c
13 | Lycopene | 160d
14 | Carotenal;Beta-Apo-8 | 160e
15 | Carotenoic acid, Methyl or Ethyl ester of Beta - Apo-8'- | 160f
16 | Flavoxanthin | 161a
17 | Canthaxanthin | 161g
18 | Beet Red (betanin) | 162
19 | Anthocyanin | 163(i)
20 | Grape Skin Extract | 163(ii)
21 | Titanium dioxide | 171"""

CANDIDATES = [
    {
        "clause_id": f"CLAUSE-{DOC_ID.upper()}-REGULATION-5-IV",
        "clause_number": "Regulation 5(iv)",
        "start_page": 1,
        "end_page": 1,
        "valid_from": datetime.date(2011, 1, 14),
        "text": """“The Food (Colouring Substances) Regulations - 2006” published in the Gazette Extraordinay, No. 1472/19 of November 23, 2006 as amended by Regulation published in the Gazette Extraordinary, No. 1585/26 of January 23, 2009 is hereby further amended as follows:-
(1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:-
“(iv) fish, molluscs, crustaceans and echinoderms;”.""",
    },
    {
        "clause_id": f"CLAUSE-{DOC_ID.upper()}-SCHEDULE-I-TABLE-I",
        "clause_number": "Schedule I Table I",
        "start_page": 1,
        "end_page": 1,
        "valid_from": datetime.date(2011, 1, 14),
        "text": """(2) in Schedule I thereto, by the repeal of Table I and II of that Schedule and the substitution therefor of the following:—

“TABLE - I
Synthetic dyes that are permitted to be used as colouring substances in food
No. | Column I Colour | Column II Common Name | Column III INS Number
1 | Red | 1 Carmoisine (Azorubine) | 122
1 | Red | 2 Ponceau 4R | 124
1 | Red | 3 Erythrosine | 127
1 | Red | 4 Allura Red | 129
2 | Yellow | 1 Sunset yellow FCF | 110
2 | Yellow | 2 Tartrazine | 102
3 | Blue | 1 Indigotine | 132
3 | Blue | 2 (Indigo carmine) | 132
3 | Blue | 3 Brilliant Blue FCF | 133
4 | Green | 1 Fast Green FCF | 143""",
    },
    {
        "clause_id": f"CLAUSE-{DOC_ID.upper()}-SCHEDULE-I-TABLE-II",
        "clause_number": "Schedule I Table II",
        "start_page": 2,
        "end_page": 2,
        "valid_from": datetime.date(2011, 1, 14),
        "text": """TABLE - II
Other Colouring substances permitted to be used
No. | Column I Natural Colouring Substances | Column II INS Number
1 | Curcumin | 100(i)
2 | Riboflavin 5' Phosphate | 101(i)
3 | Riboflavin 5' Phosphate, sodium | 101(ii)
4 | Cochineal (Carminic acid, Carmines) | 120
5 | Chlorophylls | 140
6 | Chlorophylls Copper Complex | 141(i)
7 | Caramel Class I | 150a
8 | Caramel Class III | 150c
9 | Caramel Class IV | 150d
10 | Carotenes, Natural Extracts, (Vegetable) | 160a(ii)
11 | Annatto Extracts | 160b
12 | Paprika oleoresin (Capsanthin or Capsorubin) | 160c
13 | Lycopene | 160d
14 | Carotenal;Beta-Apo-8 | 160e
15 | Carotenoic acid, Methyl or Ethyl ester of Beta - Apo-8'- | 160f
16 | Flavoxanthin | 161a
17 | Canthaxanthin | 161g
18 | Beet Red (betanin) | 162
19 | Anthocyanin | 163(i)
20 | Grape Skin Extract | 163(ii)
21 | Titanium dioxide | 171""",
    },
]


def execute_ingestion():
    # 1. Independent PDF Verification
    pdf_bytes = Path(PDF_PATH).read_bytes()
    actual_sha = hashlib.sha256(pdf_bytes).hexdigest()
    if actual_sha != EXPECTED_SHA256:
        raise ValueError(f"SHA-256 mismatch for {PDF_PATH}: {actual_sha} != {EXPECTED_SHA256}")
    logger.info("PDF hash verified: %s (%d bytes)", actual_sha, len(pdf_bytes))

    # 2. Initialize genuine local BGE embedding client
    logger.info("Initializing SentenceTransformerEmbeddingClient (BAAI/bge-base-en-v1.5)...")
    emb_client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    logger.info("Embedding client ready. Dimension: %d, verified: %s", emb_client.dimension, emb_client.is_verified)

    # 3. Generate embeddings for the 3 candidate clauses
    texts = [c["text"] for c in CANDIDATES]
    logger.info("Generating BGE embeddings for %d clauses...", len(texts))
    vectors = emb_client.embed_batch(texts)
    for i, vec in enumerate(vectors):
        if len(vec) != 768:
            raise ValueError(f"Vector {i} dimension {len(vec)} != 768")
        if any(not math.isfinite(x) for x in vec):
            raise ValueError(f"Vector {i} contains non-finite values")
    logger.info("Generated %d valid 768-dim embeddings.", len(vectors))

    # 4. Atomic Database Transaction
    with session_scope() as session:
        # A. Update Source Document metadata
        doc = session.query(SourceDocumentORM).filter_by(id=DOC_ID).one_or_none()
        if not doc:
            raise RuntimeError(f"SourceDocumentORM with id={DOC_ID} not found in database!")

        doc.title = "The Sri Lanka Gazette Extraordinary No. 1688/28 (Food Colouring Amendment 2011)"
        doc.gazette_no = "1688/28"
        doc.authority = "Minister of Health (Maithripala Sirisena)"
        doc.instrument_type = "gazette"
        doc.publication_date = datetime.date(2011, 1, 14)
        doc.extraction_status = "SUCCESS"
        doc.extraction_tool = "Windows WinRT OCR (en-GB) + PyMuPDF"
        doc.page_count = 2
        doc.is_synthetic = False
        logger.info("Updated SourceDocumentORM: %s (Gazette %s)", doc.title, doc.gazette_no)

        # B. Update DocumentPageORM text
        p1 = session.query(DocumentPageORM).filter_by(document_id=DOC_ID, page_number=1).one_or_none()
        if p1:
            p1.raw_text = PAGE_1_TEXT
            p1.char_count = len(PAGE_1_TEXT)
            p1.is_ocr = True
            p1.page_hash = hashlib.sha256(PAGE_1_TEXT.encode("utf-8")).hexdigest()
            logger.info("Updated DocumentPageORM page 1 (%d chars)", len(PAGE_1_TEXT))

        p2 = session.query(DocumentPageORM).filter_by(document_id=DOC_ID, page_number=2).one_or_none()
        if p2:
            p2.raw_text = PAGE_2_TEXT
            p2.char_count = len(PAGE_2_TEXT)
            p2.is_ocr = True
            p2.page_hash = hashlib.sha256(PAGE_2_TEXT.encode("utf-8")).hexdigest()
            logger.info("Updated DocumentPageORM page 2 (%d chars)", len(PAGE_2_TEXT))

        # C. Insert / Upsert the 3 candidate clauses
        inserted_count = 0
        for cand, vec in zip(CANDIDATES, vectors):
            existing = session.query(ClauseORM).filter_by(clause_id=cand["clause_id"], version_number=1).one_or_none()
            if existing:
                logger.info("Clause %s already exists; updating fields.", cand["clause_id"])
                clause_obj = existing
            else:
                clause_obj = ClauseORM(
                    clause_id=cand["clause_id"],
                    version_number=1,
                    document_id=DOC_ID,
                )
                session.add(clause_obj)
                inserted_count += 1

            clause_obj.clause_number = cand["clause_number"]
            clause_obj.text = cand["text"]
            clause_obj.start_page = cand["start_page"]
            clause_obj.end_page = cand["end_page"]
            clause_obj.char_start = 0
            clause_obj.char_end = len(cand["text"])
            clause_obj.valid_from = cand["valid_from"]
            clause_obj.valid_to = None
            clause_obj.transition_until = None
            clause_obj.is_compilable = True
            clause_obj.non_compilable_reason = None
            clause_obj.embedding = vec
            clause_obj.embedding_verified = True
            clause_obj.embedding_provider = emb_client.provider_name
            clause_obj.embedding_model = emb_client.model_name
            clause_obj.is_synthetic = False

            logger.info("Prepared ClauseORM: %s (%s, len=%d)", cand["clause_id"], cand["clause_number"], len(cand["text"]))

        # The session_scope context manager will commit automatically
        logger.info("Committing transaction... (%d new clauses inserted)", inserted_count)

    # 5. Read-back verification in a fresh transaction
    logger.info("Executing fresh read-back verification...")
    with session_scope() as session:
        doc = session.query(SourceDocumentORM).filter_by(id=DOC_ID).one()
        assert doc.extraction_status == "SUCCESS"
        assert doc.gazette_no == "1688/28"
        assert doc.is_synthetic is False

        p1 = session.query(DocumentPageORM).filter_by(document_id=DOC_ID, page_number=1).one()
        assert p1.raw_text == PAGE_1_TEXT
        assert p1.char_count == len(PAGE_1_TEXT)

        p2 = session.query(DocumentPageORM).filter_by(document_id=DOC_ID, page_number=2).one()
        assert p2.raw_text == PAGE_2_TEXT
        assert p2.char_count == len(PAGE_2_TEXT)

        reloaded_clauses = session.query(ClauseORM).filter_by(document_id=DOC_ID).all()
        assert len(reloaded_clauses) == 3, f"Expected 3 clauses, found {len(reloaded_clauses)}"

        for rc in reloaded_clauses:
            logger.info("Read back clause: %s | %s | pages %d-%d | embedding_len=%d | verified=%s",
                        rc.clause_id, rc.clause_number, rc.start_page, rc.end_page,
                        len(rc.embedding), rc.embedding_verified)
            assert rc.is_synthetic is False
            assert rc.embedding_verified is True
            assert rc.embedding_provider == "sentence-transformers"
            assert rc.embedding_model == "BAAI/bge-base-en-v1.5"
            assert len(rc.embedding) == 768

    logger.info("Controlled ingestion of Gazette 1688/28 clauses PASSED all verification checks.")


if __name__ == "__main__":
    execute_ingestion()
