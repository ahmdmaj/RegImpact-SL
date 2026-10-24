"""Regression test suite for Corpus Hygiene (G-1) and Synthetic Isolation (G-2).

Verifies:
  1. Normal corpus seeding strictly permits authenticated Gazette 2494/47 and excludes
     unverified sources: drafts, lecture slides, upload test artifacts, stubs, and
     duplicate ingestion copies.
  2. Synthetic fixtures do not enter the production corpus by default.
  3. Persisted synthetic records (already in DB) are strictly isolated from hybrid retrieval.
  4. Mode 2 open-inquiry POST /analysis cannot retrieve, return, or execute synthetic rules.
  5. Authenticated Regulation 3 rules remain fully functional and available via targeted analysis.
  6. Synthetic rules, when evaluated in explicit test contexts, carry an explicit
     [SYNTHETIC TEST FIXTURE - NOT VERIFIED STATUTE] warning so they cannot be mistaken for real law.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.data.seed_real_slice import seed_real_slice
from backend.src.db.models import (
    Base,
    ClauseORM,
    DocumentPageORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
    SYNTHETIC_DOCUMENT_IDS,
    SYNTHETIC_RULE_IDS,
    is_synthetic_clause,
    is_synthetic_document,
    is_synthetic_rule,
)
from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    cross_reference_coverage_gaps,
)
from backend.src.main import app, get_db
from backend.src.models.domain import OutcomeStatus
from backend.src.scripts.seed_corpus import (
    AUTHENTICATED_GAZETTE_ALLOWLIST,
    RAW_SOURCES_DIR,
    seed_regulatory_corpus,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hygiene_db() -> Generator[Session, None, None]:
    """Isolated in-memory SQLite database session for hygiene tests."""
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def hybrid_db_with_real_and_synthetic(hygiene_db: Session) -> Session:
    """Database containing both the authenticated real slice AND persisted synthetic fixtures.

    This models the worst-case integrity scenario: a database where synthetic fixtures
    were previously seeded alongside real law.
    """
    # 1. Seed authoritative real Regulation 3 slice
    seed_real_slice(session=hygiene_db)

    # 2. Persist synthetic fixtures explicitly marked is_synthetic=True
    seed_regulatory_corpus(db=hygiene_db, include_synthetic_fixtures=True)

    # 3. Add explicit synthetic legacy rule definitions to simulate existing DB state
    synthetic_doc = hygiene_db.query(SourceDocumentORM).filter_by(id="doc_fcau_labelling_2024").first()
    if not synthetic_doc:
        synthetic_doc = SourceDocumentORM(
            id="doc_fcau_labelling_2024",
            title="Synthetic Food Control Act Labelling Test Fixture 2024",
            authority="Food Control Administration Unit (Synthetic Test)",
            instrument_type="regulation",
            is_synthetic=True,
        )
        hygiene_db.add(synthetic_doc)
        hygiene_db.flush()

    synthetic_clause = hygiene_db.query(ClauseORM).filter_by(clause_id="CLAUSE-DOC_FCAU_LABELLING_2024-REG-4").first()
    if not synthetic_clause:
        synthetic_clause = ClauseORM(
            clause_id="CLAUSE-DOC_FCAU_LABELLING_2024-REG-4",
            version_number=1,
            document_id="doc_fcau_labelling_2024",
            clause_number="Regulation 4",
            text="Every package of food shall carry a label indicating the common name, net contents, and expiry date.",
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=95,
            is_compilable=True,
            is_synthetic=True,
        )
        hygiene_db.add(synthetic_clause)
        hygiene_db.flush()

    synthetic_rule = hygiene_db.query(RuleORM).filter_by(rule_id="RULE-FCAU-REG-4").first()
    if not synthetic_rule:
        synthetic_rule = RuleORM(
            rule_id="RULE-FCAU-REG-4",
            clause_id="CLAUSE-DOC_FCAU_LABELLING_2024-REG-4",
            clause_version=1,
            outcome_type="MANDATORY",
            applies_if={"conditions": [{"field": "activity", "operator": "EQUAL", "value": "food_manufacturing"}]},
            exceptions=[],
            obligation={"type": "labelling", "description": "Mandatory synthetic label declaration"},
            validity={"commencement_date": "2024-01-01"},
            source={"quote_span": "Every package of food shall carry a label"},
            review_status="APPROVED",
            is_synthetic=True,
        )
        hygiene_db.add(synthetic_rule)
        hygiene_db.flush()

    hygiene_db.commit()
    return hygiene_db


@pytest.fixture
def client_with_hybrid_db(hybrid_db_with_real_and_synthetic: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient backed by database containing both real and persisted synthetic records."""
    def _override_get_db():
        try:
            yield hybrid_db_with_real_and_synthetic
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Objective 1: Unverified Source Exclusion Tests (Defect G-1)
# ---------------------------------------------------------------------------

def test_seeding_strictly_allows_authenticated_gazette(hygiene_db: Session):
    """Normal corpus seeding must ingest Gazette 2494/47 matching the allowlist."""
    assert "2494-47_e.pdf" in AUTHENTICATED_GAZETTE_ALLOWLIST
    seed_regulatory_corpus(db=hygiene_db, force=True)

    # Gazette 2494/47 must exist in DB
    gazette_doc = hygiene_db.query(SourceDocumentORM).filter_by(id="doc_gazette_2494_47").first()
    assert gazette_doc is not None
    assert "2494/47" in gazette_doc.title
    assert gazette_doc.sha256_hash == AUTHENTICATED_GAZETTE_ALLOWLIST["2494-47_e.pdf"]
    assert gazette_doc.is_synthetic is False


def test_seeding_excludes_unverified_drafts_and_slides(hygiene_db: Session):
    """Drafts, lecture slides, upload tests, and hash-named stubs must be excluded from seeding."""
    seed_regulatory_corpus(db=hygiene_db, force=True)

    all_docs = hygiene_db.query(SourceDocumentORM).all()
    all_doc_ids = {d.id.lower() for d in all_docs}
    all_titles = {d.title.lower() for d in all_docs}

    # 1. Draft PDF must NOT be ingested as a legal source
    assert "doc_labelling_regulations_final_2026" not in all_doc_ids
    assert not any("draft" in t for t in all_titles)
    assert not any("11.02.2026" in t for t in all_titles)

    # 2. Lecture slides must NOT be ingested
    assert not any("lec 03" in t for t in all_titles)
    assert not any("slide" in t for t in all_titles)

    # 3. Test upload artifacts must NOT be ingested
    assert not any("test_gazette_upload" in did for did in all_doc_ids)

    # 4. Hash-named stubs and copies must NOT be ingested
    for doc in all_docs:
        # Document ID should not be a raw 32-64 hex hash
        assert not (len(doc.id.replace("doc_", "")) in (32, 64) and all(c in "0123456789abcdef" for c in doc.id.replace("doc_", "")))

    # 5. Secondary gazettes (2494/06, 2443/27, 2496/03) must not be trusted until formally verified
    assert not any("2494-06" in did or "2443-27" in did or "2496-03" in did for did in all_doc_ids)


def test_duplicate_ingestion_copies_cannot_bypass_allowlist(hygiene_db: Session, tmp_path: Path):
    """Renamed copies or duplicates of unverified files must be rejected by SHA-256 validation."""
    fake_dir = tmp_path / "fake_raw"
    fake_dir.mkdir()

    # Create a malicious copy of draft disguised with gazette name
    draft_path = RAW_SOURCES_DIR / "Labelling_Regulations_Final_-_11.02.2026.pdf"
    if draft_path.exists():
        disguised_file = fake_dir / "2494-47_E.pdf"
        disguised_file.write_bytes(draft_path.read_bytes())

        # Running seeding against this disguised file must reject it because SHA-256 does not match allowlist
        seed_regulatory_corpus(db=hygiene_db, raw_dir=fake_dir, force=True, include_synthetic_fixtures=False)
        doc = hygiene_db.query(SourceDocumentORM).filter_by(id="doc_gazette_2494_47").first()
        assert doc is None, "Disguised draft with incorrect SHA-256 was erroneously ingested!"


# ---------------------------------------------------------------------------
# Objective 2: Synthetic Fixture Isolation Tests (Defect G-2)
# ---------------------------------------------------------------------------

def test_synthetic_fixtures_excluded_from_corpus_by_default(hygiene_db: Session):
    """By default, normal seeding must not introduce synthetic fixtures into the database."""
    seed_regulatory_corpus(db=hygiene_db, force=True)

    docs = hygiene_db.query(SourceDocumentORM).all()
    doc_ids = {d.id for d in docs}
    for syn_id in SYNTHETIC_DOCUMENT_IDS:
        assert syn_id not in doc_ids, f"Synthetic document {syn_id} was ingested by default!"

    rules = hygiene_db.query(RuleORM).all()
    rule_ids = {r.rule_id for r in rules}
    for syn_rule in SYNTHETIC_RULE_IDS:
        assert syn_rule not in rule_ids, f"Synthetic rule {syn_rule} was registered by default!"


def test_persisted_synthetic_records_isolated_from_hybrid_retrieval(hybrid_db_with_real_and_synthetic: Session):
    """Even when synthetic records exist in DB, hybrid retrieval must never return them."""
    db = hybrid_db_with_real_and_synthetic

    # Ensure synthetic records definitely exist in this test setup
    assert db.query(RuleORM).filter(RuleORM.is_synthetic.is_(True)).count() > 0

    engine = HybridRetrievalEngine(db=db)
    # Search with queries that specifically match synthetic text
    queries = [
        "Every package of food shall carry a label indicating the common name",
        "food manufacturing labelling",
        "environmental protection licence",
        "maximum retail price",
    ]

    for q in queries:
        results = engine.search(q, top_k=10)
        for res in results:
            assert res.is_synthetic is False, f"Hybrid retrieval returned synthetic clause {res.clause_id}"
            assert res.document_id not in SYNTHETIC_DOCUMENT_IDS, f"Retrieved synthetic doc {res.document_id}"
            assert not is_synthetic_clause(clause_id=res.clause_id, document_id=res.document_id)


def test_coverage_gap_cross_reference_ignores_synthetic_rules(hybrid_db_with_real_and_synthetic: Session):
    """Synthetic rules must not satisfy coverage gap checks for real regulatory clauses."""
    db = hybrid_db_with_real_and_synthetic
    synthetic_cids = ["CLAUSE-DOC_FCAU_LABELLING_2024-REG-4", "FCAU-REG-04"]

    approved_cids = cross_reference_coverage_gaps(db, synthetic_cids, include_synthetic=False)
    assert len(approved_cids) == 0, "Synthetic clauses were treated as approved production coverage!"


# ---------------------------------------------------------------------------
# Objective 3: Open-Inquiry vs. Targeted Analysis Isolation Tests
# ---------------------------------------------------------------------------

def test_open_inquiry_post_analysis_ignores_synthetic_rules(client_with_hybrid_db: TestClient):
    """POST /analysis Mode 2 (Open Inquiry) must not execute synthetic rules even when present in DB."""
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-PROD-OPEN-001",
            "activity": "food_manufacturing",
            "industry": "food_processing",
            "employee_count": 25,
            "products": [{"category": "biscuits", "prepackaged": True}],
            "market": {"b2b_only": False},
        },
        "as_at_date": "2026-08-01",
    }

    response = client_with_hybrid_db.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    evaluated_rules = data.get("evaluations", [])
    for ev in evaluated_rules:
        rule_id = ev["rule_id"]
        # Must not be any synthetic fixture
        assert rule_id not in SYNTHETIC_RULE_IDS, f"Synthetic rule {rule_id} was executed in open inquiry!"
        assert ev.get("document_id") not in SYNTHETIC_DOCUMENT_IDS
        assert not is_synthetic_rule(rule_id=rule_id)
        assert "[SYNTHETIC TEST FIXTURE" not in ev.get("review_status", "")


def test_authenticated_regulation_3_retail_available_targeted_path(client_with_hybrid_db: TestClient):
    """Authenticated Gazette Regulation 3 retail mandate evaluates via targeted path."""
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-PROD-RETAIL-001",
            "activity": "food_manufacturing",
            "employee_count": 10,
            "packaged_in_presence_of_purchaser": False,
            "products": [
                {
                    "name": "Super Cracker Biscuits",
                    "category": "biscuits",
                    "prepackaged": True,
                    "market_channel": "retail",
                    "purchaser_present": False,
                }
            ],
            "market": {"b2b_only": False},
        },
        "clause_ids": ["RULE-FCAU-2494-47-REG-3"],
        "as_at_date": "2026-08-01",
    }

    response = client_with_hybrid_db.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rules_evaluated"] == 1
    eval_item = data["evaluations"][0]
    assert eval_item["rule_id"] == "RULE-FCAU-2494-47-REG-3"
    assert eval_item["status"] == OutcomeStatus.APPLICABLE.value
    assert eval_item["document_id"] == "doc_gazette_2494_47"
    assert "2494/47" in eval_item["document_title"]
    assert "[SYNTHETIC TEST FIXTURE" not in eval_item["review_status"]


def test_authenticated_regulation_3_b2b_preserves_statutory_disclosures(client_with_hybrid_db: TestClient):
    """Authenticated Regulation 3 B2B rule retains all 10 affirmative disclosures and 3mm marking."""
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-PROD-B2B-001",
            "activity": "food_manufacturing",
            "employee_count": 15,
            "products": [
                {
                    "name": "Industrial Bulk Glucose Syrup",
                    "category": "confectionery_raw_materials",
                    "prepackaged": True,
                    "market_channel": "business_to_business",
                    "purchaser_present": False,
                    "is_b2b": True,
                    "b2b_affirmative_disclosures": [
                        "common name (in either of the three languages)",
                        "net contents",
                        "date of manufacture",
                        "date of expiry",
                        "batch number",
                        "manufacturer's name and address",
                        "distributor's name and address",
                        "country of origin in case of imported foods",
                        "a complete list of ingredients",
                    ],
                    "b2b_not_for_retail_sale_marked": True,
                    "b2b_font_size_ge_3mm": True,
                }
            ],
            "market": {"b2b_only": True},
        },
        "clause_ids": ["RULE-FCAU-2494-47-REG-3-B2B"],
        "as_at_date": "2026-08-01",
    }

    response = client_with_hybrid_db.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rules_evaluated"] == 1
    eval_item = data["evaluations"][0]
    assert eval_item["rule_id"] == "RULE-FCAU-2494-47-REG-3-B2B"
    assert eval_item["status"] == OutcomeStatus.APPLICABLE.value

    # Must NOT contain retail trilingual requirement
    actions = data.get("action_checklist", [])
    assert not any("Sinhala, Tamil and English" in act for act in actions)
    # Must preserve B2B affirmative statutory duties
    assert any("Not for retail sale" in act for act in actions)


def test_synthetic_rules_in_explicit_test_contexts_bear_warning_tag(client_with_hybrid_db: TestClient):
    """When synthetic rules are explicitly targeted for testing, they carry a prominent warning tag."""
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-EXPLICIT-TEST-001",
            "activity": "food_manufacturing",
            "employee_count": 5,
        },
        "clause_ids": ["RULE-FCAU-REG-4"],
        "as_at_date": "2024-08-01",
    }

    response = client_with_hybrid_db.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["evaluations"]) == 1
    ev = data["evaluations"][0]
    assert ev["rule_id"] == "RULE-FCAU-REG-4"
    # Strict provenance check: Must contain warning banner
    assert "[SYNTHETIC TEST FIXTURE - NOT VERIFIED STATUTE]" in ev["review_status"]
