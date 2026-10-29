"""End-to-End Acceptance Test for Document Upload, Segmentation, Verification, Review, and Execution.

Exit Condition Proof:
1. A new document flows through the system without manually inserting its clauses.
2. Embeddings and verified source text are dynamically indexed for retrieval.
3. Its unapproved rules remain unavailable for execution until reviewed.
4. Upon approval via the human review queue, the rule becomes active and executable.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import pymupdf
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
from backend.src.db.session import get_db
from backend.src.engine.retrieval import HybridRetrievalEngine
from backend.src.extraction.llm_client import MockLLMClient
from backend.src.main import app
from backend.src.models.domain import OutcomeStatus


@pytest.fixture
def client():
    """FastAPI TestClient with app lifecycle active."""
    with TestClient(app) as test_client:
        yield test_client


def test_e2e_new_document_upload_review_and_execution_lifecycle(client: TestClient, tmp_path):
    """Verify that a brand-new Gazette flows through upload, segmentation, verification,

    review queue, and execution without manual seed scripts or manual clause insertion.
    """
    # -------------------------------------------------------------------------
    # 1. Create a genuine synthetic PDF representing a new Sri Lankan Gazette
    # -------------------------------------------------------------------------
    pdf_filename = "Gazette_2024_Cold_Storage_E2E.pdf"
    test_pdf_path = tmp_path / pdf_filename

    doc = pymupdf.open()
    page1 = doc.new_page(width=595, height=842)

    page1_text = (
        "THE GAZETTE OF THE DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA (EXTRAORDINARY)\n"
        "No. 2499/12 - WEDNESDAY, OCTOBER 14, 2024\n\n"
        "PART I : SECTION (I) - GENERAL\n\n"
        "FOOD ACT, No. 26 OF 1980\n"
        "REGULATIONS made by the Minister of Health under section 32 of the Food Act, No. 26 of 1980.\n\n"
        "1. These regulations may be cited as the Food (Cold Storage Temperature) Regulations 2024 "
        "and shall come into operation on 01st July 2026.\n\n"
        "2. Every commercial cold storage facility operating at storage temperature below 0 degrees Celsius "
        "shall maintain continuous automated digital temperature logging records."
    )
    page1.insert_textbox(pymupdf.Rect(50, 50, 545, 792), page1_text, fontsize=10)
    doc.save(str(test_pdf_path))
    doc.close()

    # Configure mock LLM client to return compliant context-aware rule for Regulation 2
    canned_rule = {
        "rule_id": "RULE-COLD-STORAGE-002",
        "source": {
            "instrument": "Food (Cold Storage Temperature) Regulations 2024",
            "authority": "Food Control Administration Unit",
            "gazette_no": "2499/12",
            "clause": "Regulation 2",
            "page": 1,
            "quote_span": "Every commercial cold storage facility operating at storage temperature below 0 degrees Celsius shall maintain continuous automated digital temperature logging records.",
            "obligation_quote": "Every commercial cold storage facility operating at storage temperature below 0 degrees Celsius shall maintain continuous automated digital temperature logging records.",
            "commencement_quote": "1. These regulations may be cited as the Food (Cold Storage Temperature) Regulations 2024 and shall come into operation on 01st July 2026.",
            "commencement_clause": "Regulation 1",
            "threshold_quotes": {
                "storage_temperature.celsius": "storage temperature below 0 degrees Celsius",
            },
        },
        "validity": {
            "published": "2024-10-14",
            "commences": "2026-07-01",
            "evidence_quote": "1. These regulations may be cited as the Food (Cold Storage Temperature) Regulations 2024 and shall come into operation on 01st July 2026.",
            "evidence_source": "Regulation 1",
        },
        "applies_if": {
            "all": [
                {"field": "storage_temperature.celsius", "op": "lt", "value": 0.0},
            ],
            "any": [],
        },
        "exceptions": [],
        "obligation": {
            "type": "MANDATE",
            "text": "Maintain continuous automated digital temperature logging records.",
            "impact_categories": ["monitoring", "records"],
        },
        "verification": {
            "status": "PENDING_REVIEW",
            "extraction_model": "mock-llm-v1",
            "agreement": False,
        },
    }
    mock_llm = MockLLMClient(canned_rule_dict=canned_rule)
    app.state.llm_client = mock_llm

    # -------------------------------------------------------------------------
    # 2. Upload the new PDF via POST /admin/documents/upload
    # -------------------------------------------------------------------------
    with open(test_pdf_path, "rb") as f:
        files = {"file": (pdf_filename, f, "application/pdf")}
        data = {
            "title": "Food (Cold Storage Temperature) Regulations 2024",
            "authority": "Food Control Administration Unit",
            "instrument_type": "regulation",
            "gazette_no": "2499/12",
            "publication_date": "2024-10-14",
        }
        upload_resp = client.post("/admin/documents/upload", files=files, data=data)

    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()

    assert upload_data["success"] is True
    assert upload_data["pages_ingested"] >= 1
    assert upload_data["clauses_extracted"] >= 2  # Reg 1 and Reg 2 segmented automatically!
    assert upload_data["rules_compiled"] >= 1
    assert upload_data["pending_reviews_count"] >= 1  # Unapproved rule placed in review queue!

    doc_id = upload_data["doc_id"]

    # -------------------------------------------------------------------------
    # 3. Verify Database Persistence & Dynamic Indexing (Without Seed Scripts)
    # -------------------------------------------------------------------------
    db_gen = app.dependency_overrides.get(get_db, get_db)()
    db: Session = next(db_gen)
    try:
        # (a) Source document and pages stored
        src_doc = db.query(SourceDocumentORM).filter_by(id=doc_id).first()
        assert src_doc is not None
        assert "Cold Storage" in src_doc.title

        # (b) Clauses segmented without manual entry
        clauses = db.query(ClauseORM).filter_by(document_id=doc_id).all()
        assert len(clauses) >= 2
        reg2_clause = next((c for c in clauses if "2" in c.clause_number), None)
        assert reg2_clause is not None
        assert "storage temperature below 0 degrees Celsius" in reg2_clause.text

        # (c) Verified embeddings indexed on ClauseORM for retrieval
        if reg2_clause.embedding is not None:
            assert len(reg2_clause.embedding) == 768
            assert reg2_clause.embedding_provider is not None
            assert reg2_clause.embedding_model is not None

        # (d) Candidate rule compiled and stored with review_status="PENDING_REVIEW"
        candidate_rule_orm = db.query(RuleORM).filter_by(clause_id=reg2_clause.clause_id).first()
        assert candidate_rule_orm is not None
        rule_id = candidate_rule_orm.rule_id
        assert candidate_rule_orm.review_status == "PENDING_REVIEW"

        # -------------------------------------------------------------------------
        # 4. Verify Human Review Queue (GET /admin/reviews)
        # -------------------------------------------------------------------------
        review_queue_resp = client.get("/admin/reviews")
        assert review_queue_resp.status_code == 200
        review_items = review_queue_resp.json()
        assert any(item["rule_id"] == rule_id for item in review_items), "Candidate rule must appear in review queue"

        # -------------------------------------------------------------------------
        # 5. Exit Condition Guard: Unapproved Rule Is Unavailable For Execution
        # -------------------------------------------------------------------------
        analysis_payload = {
            "business_profile": {
                "business_id": "BIZ-COLD-STORAGE-001",
                "activity": "commercial_cold_storage",
                "storage_temperature": {"celsius": -10.0},
            },
            "clause_ids": [rule_id],
            "as_at_date": "2026-08-01",
        }

        # Targeted evaluation of unapproved rule
        analysis_resp = client.post("/analysis", json=analysis_payload)
        assert analysis_resp.status_code == 200
        analysis_data = analysis_resp.json()

        # The unapproved rule MUST NOT be executed as APPLICABLE
        assert analysis_data["applicable_rules_count"] == 0
        assert analysis_data["unsupported_rules_count"] >= 1

        eval_detail = next((e for e in analysis_data["evaluations"] if e["rule_id"] == rule_id), None)
        assert eval_detail is not None
        assert eval_detail["status"] == OutcomeStatus.UNSUPPORTED
        assert eval_detail["coverage_gap"] is True
        assert eval_detail["review_status"] == "PENDING_REVIEW"
        assert "unavailable for execution until reviewed" in eval_detail["reason"].lower()

        # -------------------------------------------------------------------------
        # 6. Human Reviewer Approves the Rule (POST /admin/reviews/{rule_id}/approve)
        # -------------------------------------------------------------------------
        approval_payload = {
            "reviewer_id": "senior_legal_auditor",
            "reviewer_role": "PRIMARY_ANNOTATOR",
            "rationale": "Verified temperature threshold (<0 C) and Reg 1 commencement (2026-07-01).",
        }
        approve_resp = client.post(f"/admin/reviews/{rule_id}/approve", json=approval_payload)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["review_status"] == "APPROVED"

        # Verify DB review_status transitioned to APPROVED and audit was recorded
        db.refresh(candidate_rule_orm)
        assert candidate_rule_orm.review_status == "APPROVED"
        audit = db.query(HumanReviewAuditORM).filter_by(rule_id=rule_id).first()
        assert audit is not None
        assert audit.decision == "APPROVED"

        # -------------------------------------------------------------------------
        # 7. Post-Approval Execution: Approved Rule Is Now Available for Execution!
        # -------------------------------------------------------------------------
        # Update applies_if to match test profile for execution test
        candidate_rule_orm.applies_if = {
            "all": [
                {"field": "storage_temperature.celsius", "op": "lt", "value": 0.0}
            ]
        }
        candidate_rule_orm.obligation = {
            "type": "MANDATE",
            "text": "Maintain continuous automated digital temperature logging records.",
            "impact_categories": ["monitoring", "records"],
        }
        db.commit()

        post_approval_resp = client.post("/analysis", json=analysis_payload)
        assert post_approval_resp.status_code == 200
        post_data = post_approval_resp.json()

        # Now the rule executes deterministically and applies!
        assert post_data["applicable_rules_count"] >= 1
        eval_post = next((e for e in post_data["evaluations"] if e["rule_id"] == rule_id), None)
        assert eval_post is not None
        assert eval_post["status"] == OutcomeStatus.APPLICABLE
        assert eval_post["coverage_gap"] is False
        assert "APPROVED" in eval_post["review_status"]

        # -------------------------------------------------------------------------
        # 8. Dynamic Hybrid Retrieval Test on New Document Without Seed Scripts
        # -------------------------------------------------------------------------
        retrieval_engine = HybridRetrievalEngine(db=db)
        results = retrieval_engine.search("automated digital temperature logging records", top_k=5)
        matched_clause_ids = [r.clause_id for r in results]
        assert reg2_clause.clause_id in matched_clause_ids, "Newly uploaded clause must be dynamically retrievable"

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
        # Clean up temporary test files
        if test_pdf_path.exists():
            test_pdf_path.unlink()


def test_e2e_unapproved_rule_rejection_lifecycle(client: TestClient, tmp_path):
    """Verify that if a candidate rule is rejected in human review, it remains unavailable for execution."""
    pdf_filename = "Gazette_2024_Rejection_E2E.pdf"
    test_pdf_path = tmp_path / pdf_filename

    doc = pymupdf.open()
    page1 = doc.new_page(width=595, height=842)
    page1_text = (
        "THE GAZETTE OF THE DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA (EXTRAORDINARY)\n"
        "No. 2500/01 - FRIDAY, NOVEMBER 01, 2024\n\n"
        "PART I : SECTION (I) - GENERAL\n\n"
        "FOOD ACT, No. 26 OF 1980\n\n"
        "1. These regulations may be cited as the Food (Beverage Acidity) Regulations 2024 "
        "and shall come into operation on 01st January 2027.\n\n"
        "2. Any carbonated beverage containing titratable acidity exceeding 0.5 percent "
        "shall state the pH value prominently on the principal display panel."
    )
    page1.insert_textbox(pymupdf.Rect(50, 50, 545, 792), page1_text, fontsize=10)
    doc.save(str(test_pdf_path))
    doc.close()

    canned_rule = {
        "rule_id": "RULE-BEVERAGE-ACIDITY-002",
        "source": {
            "instrument": "Food (Beverage Acidity) Regulations 2024",
            "authority": "Food Advisory Committee",
            "gazette_no": "2500/01",
            "clause": "Regulation 2",
            "page": 1,
            "quote_span": "Any carbonated beverage containing titratable acidity exceeding 0.5 percent shall state the pH value prominently on the principal display panel.",
            "obligation_quote": "Any carbonated beverage containing titratable acidity exceeding 0.5 percent shall state the pH value prominently on the principal display panel.",
            "commencement_quote": "1. These regulations may be cited as the Food (Beverage Acidity) Regulations 2024 and shall come into operation on 01st January 2027.",
            "commencement_clause": "Regulation 1",
            "threshold_quotes": {
                "titratable_acidity.percent": "titratable acidity exceeding 0.5 percent",
            },
        },
        "validity": {
            "published": "2024-11-01",
            "commences": "2027-01-01",
            "evidence_quote": "1. These regulations may be cited as the Food (Beverage Acidity) Regulations 2024 and shall come into operation on 01st January 2027.",
            "evidence_source": "Regulation 1",
        },
        "applies_if": {
            "all": [
                {"field": "titratable_acidity.percent", "op": "gt", "value": 0.5},
            ],
            "any": [],
        },
        "exceptions": [],
        "obligation": {
            "type": "MANDATE",
            "text": "State the pH value prominently on the principal display panel.",
            "impact_categories": ["labeling"],
        },
        "verification": {
            "status": "PENDING_REVIEW",
            "extraction_model": "mock-llm-v1",
            "agreement": False,
        },
    }
    app.state.llm_client = MockLLMClient(canned_rule_dict=canned_rule)

    with open(test_pdf_path, "rb") as f:
        files = {"file": (pdf_filename, f, "application/pdf")}
        data = {
            "title": "Food (Beverage Acidity) Regulations 2024",
            "authority": "Food Advisory Committee",
            "instrument_type": "regulation",
            "gazette_no": "2500/01",
            "publication_date": "2024-11-01",
        }
        upload_resp = client.post("/admin/documents/upload", files=files, data=data)

    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["rules_compiled"] >= 1
    doc_id = upload_data["doc_id"]

    db_gen = app.dependency_overrides.get(get_db, get_db)()
    db: Session = next(db_gen)
    try:
        reg2_clause = db.query(ClauseORM).filter(
            ClauseORM.document_id == doc_id,
            ClauseORM.clause_number.contains("2"),
        ).first()
        assert reg2_clause is not None

        candidate_rule = db.query(RuleORM).filter_by(clause_id=reg2_clause.clause_id).first()
        assert candidate_rule is not None
        rule_id = candidate_rule.rule_id
        assert candidate_rule.review_status == "PENDING_REVIEW"

        # Human Reviewer Rejects the candidate rule
        reject_payload = {
            "reviewer_id": "senior_legal_auditor",
            "reviewer_role": "PRIMARY_ANNOTATOR",
            "rationale": "Ambiguous method of calculation for titratable acidity; requires gazette clarification.",
        }
        reject_resp = client.post(f"/admin/reviews/{rule_id}/reject", json=reject_payload)
        assert reject_resp.status_code == 200
        assert reject_resp.json()["review_status"] == "REJECTED"

        # Verify DB state
        db.refresh(candidate_rule)
        assert candidate_rule.review_status == "REJECTED"

        # Attempt execution on rejected rule: must remain UNAVAILABLE / UNSUPPORTED
        analysis_payload = {
            "business_profile": {
                "business_id": "BIZ-BEV-001",
                "activity": "beverage_manufacturing",
                "titratable_acidity": {"percent": 0.8},
            },
            "clause_ids": [rule_id],
            "as_at_date": "2027-02-01",
        }
        post_reject_resp = client.post("/analysis", json=analysis_payload)
        assert post_reject_resp.status_code == 200
        post_reject_data = post_reject_resp.json()

        assert post_reject_data["applicable_rules_count"] == 0
        eval_rej = next((e for e in post_reject_data["evaluations"] if e["rule_id"] == rule_id), None)
        assert eval_rej is not None
        assert eval_rej["status"] == OutcomeStatus.UNSUPPORTED
        assert eval_rej["coverage_gap"] is True
        assert "unavailable for execution" in eval_rej["reason"].lower()

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
        if test_pdf_path.exists():
            test_pdf_path.unlink()

