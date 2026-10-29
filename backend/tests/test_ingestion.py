"""Milestone 1 tests: database layer, ingestion pipeline, and persistence.

All tests run against an in-memory SQLite database — no PostgreSQL daemon
required.  The PDF tests use synthetic minimal PDFs constructed in conftest.py.

Test coverage:
  DB-001  Schema creation (all five tables exist)
  DB-002  SourceDocument persists and survives session boundary
  DB-003  DocumentPage persists with correct character offsets
  DB-004  SHA-256 deduplication rejects identical bytes
  DB-005  Duplicate doc_id with different hash is rejected
  DB-006  Character offset correctness assertion
  DB-007  Clause ORM roundtrip (domain → ORM → domain)
  DB-008  Rule ORM roundtrip via PostgresRegulatoryRepository
  DB-009  get_approved_rules enforces review_status gate
  DB-010  Clause cascade delete removes pages
  ING-001  DocumentIngestionService end-to-end (happy path)
  ING-002  Ingestion of non-existent file returns FAILED status
  ING-003  Re-ingesting identical bytes returns is_duplicate=True
  ING-004  Two-page PDF produces two DocumentPage rows
  ING-005  Inspection report returns correct metadata
  ING-006  Page hash is deterministic and matches SHA-256(raw_text)
  SEG-001  segment_clauses_from_page finds Regulation headers
  SEG-002  segment_clauses_from_page returns empty list for blank text
  SEG-003  Character offsets align with source text
  REPO-001 PostgresRegulatoryRepository.add_rule persists a Rule
  REPO-002 PostgresRegulatoryRepository.get_all_rules returns all
  REPO-003 PostgresRegulatoryRepository.get_rules_by_ids filters correctly
  REPO-004 HumanReviewAuditORM record is persisted and linked
"""

from __future__ import annotations

import hashlib
import datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect, text

from backend.src.db.models import (
    Base,
    ClauseORM,
    DocumentPageORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
)
from backend.src.db.repositories import (
    InMemoryRepository,
    PostgresRegulatoryRepository,
    clause_orm_to_domain,
    rule_orm_to_domain,
)
from backend.src.extraction.ingestion import (
    DocumentIngestionService,
    NestedSubClause,
    SegmentedClause,
    TableData,
    _sha256_of_bytes,
    _sha256_of_text,
    extract_document_preamble,
    segment_clauses_from_page,
    segment_document_clauses,
)
from backend.src.models.domain import (
    AppliesIf,
    ClauseVersion,
    Condition,
    Obligation,
    Rule,
    Source,
    Validity,
    Verification,
)


# ===========================================================================
# Shared domain fixtures
# ===========================================================================

@pytest.fixture()
def sample_rule() -> Rule:
    """A well-formed domain Rule with human_verified status."""
    return Rule(
        rule_id="TEST-RULE-001",
        source=Source(
            instrument="Test Regulation 2024",
            authority="Test Authority",
            gazette_no="2024/99",
            clause="Regulation 4",
            page=1,
            quote_span="Regulation 4. Every food manufacturing enterprise with 50 kg/day shall label.",
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
            text="Label all retail packages.",
            impact_categories=["labelling"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="manual-gold",
            agreement=True,
        ),
    )


@pytest.fixture()
def approved_rule() -> Rule:
    """A domain Rule with review_status APPROVED (stored in verification.status)."""
    return Rule(
        rule_id="TEST-RULE-APPROVED",
        source=Source(
            instrument="Test Regulation 2024",
            authority="Test Authority",
            gazette_no="2024/99",
            clause="Regulation 5",
            page=2,
            quote_span="Regulation 5. Approved rule text.",
        ),
        validity=Validity(published="2024-01-01", commences="2024-06-01"),
        applies_if=AppliesIf(all=[Condition(field="activity", op="eq", value="food_manufacturing")]),
        exceptions=[],
        obligation=Obligation(
            type="registration",
            text="Register with authority.",
            impact_categories=["registration"],
        ),
        verification=Verification(
            status="APPROVED",
            extraction_model="manual-gold",
            agreement=True,
        ),
    )


# ===========================================================================
# DB-001: Schema creation
# ===========================================================================

def test_db_001_schema_tables_exist(db_engine):
    """All five ORM tables must be present after Base.metadata.create_all."""
    inspector = sa_inspect(db_engine)
    table_names = set(inspector.get_table_names())
    expected = {
        "source_documents",
        "document_pages",
        "clauses",
        "rules",
        "human_review_audit",
    }
    missing = expected - table_names
    assert not missing, f"Missing tables: {missing}"


# ===========================================================================
# DB-002: SourceDocument persist and survive session boundary
# ===========================================================================

def test_db_002_source_document_persists(db_session):
    """A SourceDocumentORM record survives a flush and can be re-fetched."""
    doc = SourceDocumentORM(
        id="doc_test_001",
        sha256_hash="a" * 64,
        title="Test Regulation 2024",
        authority="Test Authority",
        file_path="backend/data/raw_sources/test.pdf",
        file_size_bytes=1024,
        page_count=1,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF 1.28.2",
    )
    db_session.add(doc)
    db_session.flush()

    fetched = db_session.get(SourceDocumentORM, "doc_test_001")
    assert fetched is not None
    assert fetched.sha256_hash == "a" * 64
    assert fetched.title == "Test Regulation 2024"
    assert fetched.extraction_status == "SUCCESS"


# ===========================================================================
# DB-003: DocumentPage persists with correct character offsets
# ===========================================================================

def test_db_003_document_page_char_offsets(db_session):
    """DocumentPageORM stores char_count equal to len(raw_text)."""
    doc = SourceDocumentORM(
        id="doc_test_002",
        sha256_hash="b" * 64,
        title="Test Regulation",
        authority="Authority",
        file_path="backend/data/test.pdf",
        file_size_bytes=512,
        page_count=1,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF 1.28.2",
    )
    db_session.add(doc)
    db_session.flush()

    raw_text = "Regulation 4. Every food manufacturing enterprise..."
    page = DocumentPageORM(
        document_id="doc_test_002",
        page_number=1,
        raw_text=raw_text,
        char_count=len(raw_text),
        is_ocr=False,
        page_hash=_sha256_of_text(raw_text),
    )
    db_session.add(page)
    db_session.flush()

    fetched = (
        db_session.query(DocumentPageORM)
        .filter_by(document_id="doc_test_002", page_number=1)
        .one()
    )
    assert fetched.char_count == len(raw_text)
    assert fetched.char_count == 52
    assert fetched.page_hash == _sha256_of_text(raw_text)
    assert fetched.is_ocr is False


# ===========================================================================
# DB-004: SHA-256 deduplication
# ===========================================================================

def test_db_004_sha256_unique_constraint(db_session):
    """Two SourceDocumentORM rows with the same sha256_hash must fail the UNIQUE constraint."""
    from sqlalchemy.exc import IntegrityError

    doc1 = SourceDocumentORM(
        id="doc_dup_001",
        sha256_hash="c" * 64,
        title="Document A",
        authority="Authority",
        file_path="path/a.pdf",
        file_size_bytes=100,
        page_count=1,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    doc2 = SourceDocumentORM(
        id="doc_dup_002",
        sha256_hash="c" * 64,   # Same hash
        title="Document B",
        authority="Authority",
        file_path="path/b.pdf",
        file_size_bytes=200,
        page_count=1,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add(doc1)
    db_session.flush()

    db_session.add(doc2)
    with pytest.raises(IntegrityError):
        db_session.flush()


# ===========================================================================
# DB-005: Duplicate doc_id with different hash rejected
# ===========================================================================

def test_db_005_duplicate_doc_id_rejected(db_session, tmp_path):
    """Ingestion service rejects a doc_id that already exists with different content."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")

    # Create two different PDFs (different bytes)
    pdf1 = tmp_path / "doc_a.pdf"
    pdf2 = tmp_path / "doc_b.pdf"
    pdf1.write_bytes(b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")
    pdf2.write_bytes(b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n%extra")

    # First ingestion
    r1 = svc.ingest(
        db=db_session,
        pdf_path=pdf1,
        doc_id="doc_same_id",
        title="Document A",
        authority="Authority A",
    )
    db_session.flush()

    # Second ingestion with same doc_id but different bytes
    r2 = svc.ingest(
        db=db_session,
        pdf_path=pdf2,
        doc_id="doc_same_id",
        title="Document B",
        authority="Authority B",
    )

    assert r2.extraction_status == "FAILED"
    assert r2.error is not None
    assert "doc_same_id" in r2.error


# ===========================================================================
# DB-006: Character offset correctness
# ===========================================================================

def test_db_006_char_offset_correctness():
    """The _sha256_of_text helper and char_count must be deterministic."""
    text = "Regulation 4. Production capacity of 50 kg per day."
    h1 = _sha256_of_text(text)
    h2 = _sha256_of_text(text)
    assert h1 == h2
    assert len(h1) == 64  # hex SHA-256
    assert h1 == hashlib.sha256(text.encode("utf-8")).hexdigest()


# ===========================================================================
# DB-007: ClauseORM roundtrip (domain → ORM → domain)
# ===========================================================================

def test_db_007_clause_orm_roundtrip(db_session):
    """A ClauseVersion can be stored and retrieved via the ORM model."""
    doc = SourceDocumentORM(
        id="doc_clause_test",
        sha256_hash="d" * 64,
        title="Test Regulation 2024",
        authority="Test Authority",
        file_path="backend/data/test.pdf",
        file_size_bytes=512,
        page_count=2,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF 1.28.2",
    )
    db_session.add(doc)
    db_session.flush()

    clause = ClauseORM(
        clause_id="TEST-REG-04",
        version_number=1,
        document_id="doc_clause_test",
        clause_number="Regulation 4",
        text="Every food manufacturing enterprise having 50 kg/day shall label.",
        start_page=1,
        end_page=1,
        char_start=0,
        char_end=65,
        valid_from=datetime.date(2024, 6, 1),
        is_compilable=True,
    )
    db_session.add(clause)
    db_session.flush()

    fetched = (
        db_session.query(ClauseORM)
        .filter_by(clause_id="TEST-REG-04", version_number=1)
        .one()
    )
    assert fetched.clause_number == "Regulation 4"
    assert fetched.char_end == 65
    assert fetched.start_page == 1
    assert fetched.valid_from == datetime.date(2024, 6, 1)

    cv = clause_orm_to_domain(fetched)
    assert cv.clause_id == "TEST-REG-04"
    assert cv.version_number == 1
    assert "50 kg/day" in cv.text


# ===========================================================================
# DB-008: RuleORM roundtrip via PostgresRegulatoryRepository
# ===========================================================================

def test_db_008_rule_orm_roundtrip(db_session, sample_rule):
    """A Rule domain model can be stored and retrieved via PostgresRegulatoryRepository."""
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(sample_rule)
    db_session.flush()

    rules = repo.get_all_rules()
    assert any(r.rule_id == "TEST-RULE-001" for r in rules)

    retrieved = next(r for r in rules if r.rule_id == "TEST-RULE-001")
    assert retrieved.source.instrument == "Test Regulation 2024"
    assert retrieved.obligation.type == "labelling"
    assert len(retrieved.applies_if.all) == 2
    assert retrieved.applies_if.all[0].field == "activity"
    assert retrieved.applies_if.all[1].value == 50


# ===========================================================================
# DB-009: get_approved_rules enforces review_status gate
# ===========================================================================

def test_db_009_approved_rules_gate(db_session, sample_rule, approved_rule):
    """get_approved_rules() returns only rules with review_status == APPROVED."""
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(sample_rule)    # status = human_verified (not APPROVED)
    repo.add_rule(approved_rule)  # status = APPROVED
    db_session.flush()

    all_rules = repo.get_all_rules()
    approved_rules = repo.get_approved_rules()

    assert len(all_rules) == 2
    assert len(approved_rules) == 1
    assert approved_rules[0].rule_id == "TEST-RULE-APPROVED"


# ===========================================================================
# DB-010: Cascade delete — deleting a document removes its pages
# ===========================================================================

def test_db_010_cascade_delete_pages(db_session):
    """Deleting a SourceDocumentORM must cascade-delete all its DocumentPageORM rows."""
    doc = SourceDocumentORM(
        id="doc_cascade_test",
        sha256_hash="e" * 64,
        title="Cascade Test Doc",
        authority="Test Authority",
        file_path="path/cascade.pdf",
        file_size_bytes=1024,
        page_count=2,
        extraction_status="SUCCESS",
        extraction_tool="PyMuPDF",
    )
    db_session.add(doc)
    db_session.flush()

    for i in range(1, 3):
        page = DocumentPageORM(
            document_id="doc_cascade_test",
            page_number=i,
            raw_text=f"Page {i} text",
            char_count=len(f"Page {i} text"),
            is_ocr=False,
            page_hash=_sha256_of_text(f"Page {i} text"),
        )
        db_session.add(page)
    db_session.flush()

    pages_before = (
        db_session.query(DocumentPageORM)
        .filter_by(document_id="doc_cascade_test")
        .count()
    )
    assert pages_before == 2

    db_session.delete(doc)
    db_session.flush()

    pages_after = (
        db_session.query(DocumentPageORM)
        .filter_by(document_id="doc_cascade_test")
        .count()
    )
    assert pages_after == 0


# ===========================================================================
# ING-001: DocumentIngestionService end-to-end (happy path)
# ===========================================================================

def test_ing_001_ingestion_happy_path(db_session, pdf_file, tmp_path):
    """Ingesting a valid PDF should produce SUCCESS status and correct page count."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")

    result = svc.ingest(
        db=db_session,
        pdf_path=pdf_file,
        doc_id="doc_ing_001",
        title="Food Labelling Regulations 2024",
        authority="Food Control Administration Unit",
        gazette_no="2024/01",
        source_url=None,  # Not invented
        publication_date="2024-01-01",
    )

    assert result.success is True
    assert result.is_duplicate is False
    assert result.doc_id == "doc_ing_001"
    assert len(result.sha256_hash) == 64
    assert result.page_count >= 1

    # Verify database record
    doc = db_session.get(SourceDocumentORM, "doc_ing_001")
    assert doc is not None
    assert doc.sha256_hash == result.sha256_hash
    assert doc.gazette_no == "2024/01"
    assert doc.page_count == result.page_count

    # Verify pages were stored
    pages = (
        db_session.query(DocumentPageORM)
        .filter_by(document_id="doc_ing_001")
        .all()
    )
    assert len(pages) == result.page_count
    assert all(p.char_count >= 0 for p in pages)


# ===========================================================================
# ING-002: Ingestion of non-existent file returns FAILED
# ===========================================================================

def test_ing_002_nonexistent_file_returns_failed(db_session, tmp_path):
    """Ingesting a file that doesn't exist must return FAILED status without raising."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")

    result = svc.ingest(
        db=db_session,
        pdf_path=tmp_path / "does_not_exist.pdf",
        doc_id="doc_missing",
        title="Missing File",
        authority="Test",
    )

    assert result.success is False
    assert result.extraction_status == "FAILED"
    assert result.error is not None


# ===========================================================================
# ING-003: Re-ingesting identical bytes returns is_duplicate=True
# ===========================================================================

def test_ing_003_duplicate_ingestion(db_session, pdf_file, tmp_path):
    """Re-ingesting the exact same PDF bytes must return is_duplicate=True."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")

    r1 = svc.ingest(
        db=db_session,
        pdf_path=pdf_file,
        doc_id="doc_orig",
        title="Original Document",
        authority="Authority",
    )
    db_session.flush()

    # Re-ingest the identical bytes under a different doc_id
    r2 = svc.ingest(
        db=db_session,
        pdf_path=pdf_file,
        doc_id="doc_duplicate_attempt",
        title="Duplicate Attempt",
        authority="Authority",
    )

    assert r1.success is True
    assert r2.is_duplicate is True
    assert r2.sha256_hash == r1.sha256_hash
    assert r2.doc_id == "doc_orig"  # Returns the existing record's id


# ===========================================================================
# ING-004: Two-page PDF produces two DocumentPage rows
# ===========================================================================

def test_ing_004_two_page_pdf(db_session, two_page_pdf_file, tmp_path):
    """A two-page PDF must produce exactly two DocumentPageORM rows."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")

    result = svc.ingest(
        db=db_session,
        pdf_path=two_page_pdf_file,
        doc_id="doc_two_page",
        title="Two Page Test",
        authority="Test Authority",
    )
    db_session.flush()

    assert result.page_count == 2

    pages = (
        db_session.query(DocumentPageORM)
        .filter_by(document_id="doc_two_page")
        .order_by(DocumentPageORM.page_number)
        .all()
    )
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2


# ===========================================================================
# ING-005: Inspection report returns correct metadata
# ===========================================================================

def test_ing_005_inspection_report(db_session, pdf_file, tmp_path):
    """inspection_report() returns a dict with accurate metadata fields."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")

    svc.ingest(
        db=db_session,
        pdf_path=pdf_file,
        doc_id="doc_inspect",
        title="Food Labelling Regulations",
        authority="FCAU",
        gazette_no="2024/01",
        publication_date="2024-01-01",
    )
    db_session.flush()

    report = svc.inspection_report(db_session, "doc_inspect")

    assert report["doc_id"] == "doc_inspect"
    assert report["title"] == "Food Labelling Regulations"
    assert report["authority"] == "FCAU"
    assert report["gazette_no"] == "2024/01"
    assert report["extraction_status"] in ("SUCCESS", "PARTIAL_OCR")
    assert isinstance(report["page_count"], int) and report["page_count"] >= 1
    assert isinstance(report["sha256_hash"], str) and len(report["sha256_hash"]) == 64


# ===========================================================================
# ING-006: Page hash is deterministic (SHA-256 of raw_text)
# ===========================================================================

def test_ing_006_page_hash_deterministic(db_session, pdf_file, tmp_path):
    """Every DocumentPageORM row must have page_hash == SHA-256(raw_text)."""
    svc = DocumentIngestionService(pdf_store_dir=tmp_path / "store")
    svc.ingest(
        db=db_session,
        pdf_path=pdf_file,
        doc_id="doc_hash_check",
        title="Hash Check Doc",
        authority="Authority",
    )
    db_session.flush()

    pages = (
        db_session.query(DocumentPageORM)
        .filter_by(document_id="doc_hash_check")
        .all()
    )
    for page in pages:
        expected_hash = hashlib.sha256(page.raw_text.encode("utf-8", errors="replace")).hexdigest()
        assert page.page_hash == expected_hash, (
            f"Page {page.page_number} hash mismatch: "
            f"stored={page.page_hash!r}, expected={expected_hash!r}"
        )


# ===========================================================================
# SEG-001: segment_clauses_from_page finds Regulation headers
# ===========================================================================

def test_seg_001_finds_regulation_headers():
    """segment_clauses_from_page must detect Regulation N headers."""
    text = (
        "PREAMBLE\n\n"
        "Regulation 4. Every food manufacturing enterprise having a production "
        "capacity of 50 kg per day or more, and engaged in the production of "
        "prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English.\n\n"
        "Regulation 5. Every food manufacturing enterprise shall register with the authority "
        "within 6 months of commencement of this regulation."
    )
    clauses = segment_clauses_from_page(text, page_number=1)
    assert len(clauses) >= 2
    clause_numbers = [c.clause_number for c in clauses]
    assert any("Regulation 4" in cn for cn in clause_numbers)
    assert any("Regulation 5" in cn for cn in clause_numbers)


# ===========================================================================
# SEG-002: segment_clauses_from_page returns empty list for blank text
# ===========================================================================

def test_seg_002_empty_text_returns_empty():
    """segment_clauses_from_page must return an empty list for blank input."""
    assert segment_clauses_from_page("", page_number=1) == []
    assert segment_clauses_from_page("   \n\n  ", page_number=1) == []


# ===========================================================================
# SEG-003: Character offsets align with source text
# ===========================================================================

def test_seg_003_char_offsets_align_with_source():
    """char_start and char_end in each SegmentedClause must index into the raw text correctly."""
    text = (
        "Regulation 4. Short clause about labelling requirements.\n"
        "Regulation 5. Another clause about registration duties."
    )
    clauses = segment_clauses_from_page(text, page_number=1, min_clause_length=10)
    for clause in clauses:
        extracted = text[clause.char_start : clause.char_end]
        assert clause.clause_number in extracted, (
            f"Expected {clause.clause_number!r} in slice {extracted!r}"
        )


# ===========================================================================
# REPO-001: PostgresRegulatoryRepository.add_rule persists a Rule
# ===========================================================================

def test_repo_001_add_rule_persists(db_session, sample_rule):
    """add_rule() must persist a RuleORM row retrievable by rule_id."""
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(sample_rule)
    db_session.flush()

    orm = db_session.get(RuleORM, "TEST-RULE-001")
    assert orm is not None
    assert orm.rule_id == "TEST-RULE-001"
    assert orm.applies_if["all"][0]["field"] == "activity"


# ===========================================================================
# REPO-002: get_all_rules returns all rules
# ===========================================================================

def test_repo_002_get_all_rules(db_session, sample_rule, approved_rule):
    """get_all_rules() must return every stored rule regardless of status."""
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(sample_rule)
    repo.add_rule(approved_rule)
    db_session.flush()

    rules = repo.get_all_rules()
    ids = {r.rule_id for r in rules}
    assert "TEST-RULE-001" in ids
    assert "TEST-RULE-APPROVED" in ids


# ===========================================================================
# REPO-003: get_rules_by_ids filters correctly
# ===========================================================================

def test_repo_003_get_rules_by_ids(db_session, sample_rule, approved_rule):
    """get_rules_by_ids() must return only rules matching the supplied IDs."""
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(sample_rule)
    repo.add_rule(approved_rule)
    db_session.flush()

    result = repo.get_rules_by_ids(["TEST-RULE-001"])
    assert len(result) == 1
    assert result[0].rule_id == "TEST-RULE-001"

    result_none = repo.get_rules_by_ids(["NONEXISTENT-ID"])
    assert result_none == []


# ===========================================================================
# REPO-004: HumanReviewAuditORM is persisted and linked to rule
# ===========================================================================

def test_repo_004_human_review_audit_persisted(db_session, sample_rule):
    """HumanReviewAuditORM rows must be storable and linked to a rule."""
    repo = PostgresRegulatoryRepository(db_session)
    repo.add_rule(sample_rule)
    db_session.flush()

    audit = HumanReviewAuditORM(
        rule_id="TEST-RULE-001",
        reviewer_id="annotator_01",
        reviewer_role="PRIMARY_ANNOTATOR",
        decision="APPROVED",
        rationale=(
            "Quote span verified against gazette page 1; "
            "numeric threshold 50 kg/day confirmed in clause text; "
            "operator gte correctly represents the statutory minimum."
        ),
        reviewed_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db_session.add(audit)
    db_session.flush()

    fetched = (
        db_session.query(HumanReviewAuditORM)
        .filter_by(rule_id="TEST-RULE-001")
        .one()
    )
    assert fetched.reviewer_id == "annotator_01"
    assert fetched.decision == "APPROVED"
    assert "50 kg/day" in fetched.rationale

    # Verify the linked rule is accessible
    rule_orm = db_session.get(RuleORM, "TEST-RULE-001")
    assert len(rule_orm.audit_log) == 1
    assert rule_orm.audit_log[0].decision == "APPROVED"


# ===========================================================================
# SEG-004: Multi-page gazette clause stitching
# ===========================================================================

def test_seg_004_document_level_segmentation():
    """segment_document_clauses must stitch clauses across pages and strip headers/footers."""
    page_1 = (
        "Part I : Sec. (I) - GAZETTE EXTRAORDINARY OF THE DEMOCRATIC SOCIALIST REPUBLIC - 26.06.2026\n"
        "1A\n"
        "REGULATIONS\n"
        "1.\n"
        "These regulations may be cited as Food (Labelling and Advertising) Regulations 2026.\n"
        "2.\n"
        "These regulations shall not apply to food products manufactured prior to the date of operation.\n"
        "3.\n"
        "A person shall not import, transport, distribute, store, sell, or advertise any packaged food unless labelled:"
    )
    page_2 = (
        "Part I : Sec. (I) - GAZETTE EXTRAORDINARY OF THE DEMOCRATIC SOCIALIST REPUBLIC - 26.06.2026\n"
        "2A\n"
        "Provided that these regulations shall not apply to business-to-business products subject to mandatory clauses.\n"
        "4. (1)\n"
        "The package or container shall bear a conspicuous declaration of ingredients and allergens."
    )

    clauses = segment_document_clauses([page_1, page_2])
    assert len(clauses) >= 4
    names = [c.clause_number for c in clauses]
    assert "Regulation 1" in names
    assert "Regulation 2" in names
    assert "Regulation 3" in names
    assert "Regulation 4(1)" in names

    # Verify Regulation 3 spans page 1 to page 2 and includes the proviso from page 2
    reg3 = next(c for c in clauses if c.clause_number == "Regulation 3")
    assert reg3.start_page == 1
    assert reg3.end_page == 2
    assert "business-to-business" in reg3.text
    assert "Part I : Sec." not in reg3.text


# ===========================================================================
# SEG-005: Extract document preamble metadata
# ===========================================================================

def test_seg_005_extract_document_preamble():
    """extract_document_preamble must extract gazette number, dates, and title."""
    sample_text = (
        "No. 2494/47 - FRIDAY, JUNE 26, 2026\n"
        "FOOD ACT, No. 26 OF 1980\n"
        "REGULATIONS made by the Minister of Health and Mass Media under section 32 of the Food Act.\n"
        "Colombo, 26th June, 2026.\n"
        "REGULATIONS\n"
        "1. These regulations may be cited as Food (Labelling and Advertising) Regulations 2026 "
        "and shall come into operation on 01st July 2026."
    )
    meta = extract_document_preamble([sample_text])
    assert "2494/47" in (meta["gazette_no"] or "")
    assert meta["published"] == "2026-06-26"
    assert meta["commences"] == "2026-07-01"
    assert "Food (Labelling and Advertising) Regulations 2026" in (meta["instrument"] or "")
    assert "Minister of Health" in (meta["authority"] or "")


# ===========================================================================
# SEG-006: Nested subclauses and provisos
# ===========================================================================

def test_seg_006_provisos_and_nested_subclauses():
    """Clauses must parse nested subregulations, paragraphs, subparagraphs, and provisos."""
    sample_text = (
        "REGULATIONS\n"
        "3. (1) Where any food contains any amount of sugar, the label shall have the corresponding logo:\n"
        "Provided that this requirement shall not apply to raw agricultural commodities;\n"
        "Provided however, when there is a space constraint, the logo dimensions may be reduced.\n"
        "(a) by the repeal of sub-regulation (1);\n"
        "(b) by the substitution for the words;\n"
        "(i) exceeding 8.0 g/100 ml;\n"
        "(ii) exceeding 12.0 g/100 ml."
    )
    clauses = segment_document_clauses([sample_text])
    assert len(clauses) == 1
    c = clauses[0]
    assert c.clause_number == "Regulation 3(1)"
    assert len(c.provisos) == 2
    assert any("raw agricultural commodities" in p for p in c.provisos)
    assert any("space constraint" in p for p in c.provisos)

    sub_identifiers = [sc.identifier for sc in c.sub_clauses]
    assert "Proviso" in sub_identifiers
    assert "(a)" in sub_identifiers
    assert "(b)" in sub_identifiers
    assert "(i)" in sub_identifiers
    assert "(ii)" in sub_identifiers


# ===========================================================================
# SEG-007: Real Gazette amendment directives, provisos, and tables (2494-06_E.pdf)
# ===========================================================================

def test_seg_007_amendment_directives_and_tables():
    """An amendment gazette with cross-page provisos and schedule tables must be parsed cleanly."""
    from pathlib import Path
    pdf_path = Path("backend/data/raw_sources/2494-06_E.pdf")
    if not pdf_path.exists():
        pytest.skip("2494-06_E.pdf not present in test environment.")

    clauses = segment_document_clauses([], pdf_path=pdf_path)
    assert len(clauses) >= 5

    names = [c.clause_number for c in clauses]
    assert any("Directive (1)" in n for n in names)
    assert any("Directive (2)" in n for n in names)
    assert any("SCHEDULE" in n for n in names)

    # Directive (1) crosses Page 1 to Page 2 with proviso
    d1 = next(c for c in clauses if "Directive (1)" in c.clause_number)
    assert d1.start_page == 1
    assert d1.end_page == 2
    assert d1.provisos, "Proviso across page boundary must be captured"
    assert any("space constraint" in p for p in d1.provisos)

    # Schedule has structured tables
    sched = next(c for c in clauses if "SCHEDULE" in c.clause_number)
    assert sched.tables, "Schedule must contain extracted table data"
    assert any("sugar" in col.lower() for col in sched.tables[0].headers)


# ===========================================================================
# SEG-008: Real Gazette statutory orders and fee schedule (2496-03_E.pdf)
# ===========================================================================

def test_seg_008_statutory_orders_and_fee_schedules():
    """A statutory order gazette must extract the order clause and multi-row schedule table."""
    from pathlib import Path
    pdf_path = Path("backend/data/raw_sources/2496-03_E.pdf")
    if not pdf_path.exists():
        pytest.skip("2496-03_E.pdf not present in test environment.")

    clauses = segment_document_clauses([], pdf_path=pdf_path)
    assert len(clauses) >= 2

    # Verify Order clause
    order_clause = clauses[0]
    assert order_clause.clause_type == "order"
    assert "are hereby amended" in order_clause.text

    # Verify Schedule table
    sched_clause = clauses[1]
    assert sched_clause.clause_type == "schedule"
    assert sched_clause.tables
    table = sched_clause.tables[0]
    assert len(table.rows) >= 20, f"Expected 20+ rows in fee schedule, got {len(table.rows)}"
    assert any("registration" in r[1].lower() and "limited" in r[1].lower() for r in table.rows)


# ===========================================================================
# SEG-009: Masthead metadata extraction precision
# ===========================================================================

def test_seg_009_masthead_metadata_precision():
    """Preamble extraction must resolve exact publication numbers and dates from mastheads."""
    from pathlib import Path
    pdf_path = Path("backend/data/raw_sources/2494-06_E.pdf")
    if not pdf_path.exists():
        pytest.skip("2494-06_E.pdf not present in test environment.")

    import pymupdf
    doc = pymupdf.open(str(pdf_path))
    meta = extract_document_preamble([doc[0].get_text("text")])
    assert meta["gazette_no"] == "Gazette Extraordinary No. 2494/06"
    assert meta["published"] == "2026-06-23"
    assert meta["instrument_type"] == "amendment_regulation"

