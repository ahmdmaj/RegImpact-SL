"""Integration tests for FastAPI application layer."""

import pytest
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.models.domain import OutcomeStatus


@pytest.fixture
def client():
    """Fixture providing a TestClient for FastAPI app with lifespan active."""
    with TestClient(app) as test_client:
        yield test_client


# 1. Test GET /health
def test_get_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# 2. Test GET /regulations
def test_get_regulations(client: TestClient):
    response = client.get("/regulations")
    assert response.status_code == 200
    regulations = response.json()
    assert isinstance(regulations, list)
    assert len(regulations) >= 2

    clause_ids = [r["clause_id"] for r in regulations]
    assert "FCAU-REG-04" in clause_ids
    assert "CEA-SCHED-01-B12" in clause_ids


# 3. Test POST /analysis with valid profile -> APPLICABLE + mapped impacts + trace
def test_post_analysis_applicable_profile(client: TestClient):
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-001",
            "activity": "food_manufacturing",
            "employee_count": 25,
            "products": [{"category": "biscuits", "prepackaged": True}],
            "production_capacity": {"value": 100.0, "unit": "kg", "per_period": "day"},
        },
        "as_at_date": "2024-08-01",
    }

    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["as_at_date"] == "2024-08-01"
    assert data["total_rules_evaluated"] >= 2
    assert data["applicable_rules_count"] >= 1

    # Verify action checklist and affected activities aggregated
    assert len(data["action_checklist"]) > 0
    assert len(data["affected_activities"]) > 0
    assert len(data["affected_documents"]) > 0

    # Find the FCAU labelling rule in evaluations
    fcau_eval = next((e for e in data["evaluations"] if e["rule_id"] == "RULE-FCAU-001"), None)
    assert fcau_eval is not None
    assert fcau_eval["status"] == OutcomeStatus.APPLICABLE.value
    assert fcau_eval["impact"] is not None
    assert fcau_eval["impact"]["obligation_type"] == "labelling"
    assert len(fcau_eval["impact"]["action_items"]) > 0

    # Verify evaluation trace
    trace = fcau_eval["evaluation_trace"]
    assert len(trace) == 3
    assert all(t["result"] == "TRUE" for t in trace)


# 4. Test POST /analysis with incomplete profile -> CONDITIONAL_MISSING_DATA + clarifying questions
def test_post_analysis_incomplete_profile(client: TestClient):
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-002",
            "activity": "food_manufacturing",
            "products": [{"category": "confectionery", "prepackaged": True}],
            "production_capacity": None,  # Omitted required capacity
        },
        "as_at_date": "2024-08-01",
        "clause_ids": ["RULE-FCAU-001"],
    }

    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rules_evaluated"] == 1
    assert data["conditional_rules_count"] == 1
    assert data["applicable_rules_count"] == 0

    # Missing field identification
    assert "production_capacity.kg_per_day" in data["missing_fields"]

    # Clarifying questions generated
    assert len(data["clarifying_questions"]) > 0
    capacity_question = next(
        (q for q in data["clarifying_questions"] if "daily production capacity" in q.lower()),
        None,
    )
    assert capacity_question is not None

    # Check evaluation details
    eval_item = data["evaluations"][0]
    assert eval_item["status"] == OutcomeStatus.CONDITIONAL_MISSING_DATA.value
    assert "production_capacity.kg_per_day" in eval_item["missing_fields"]
    # No false positive impact actions for conditional missing data
    assert eval_item["impact"] is None


# 5. Test POST /analysis with selective clause_ids filter
def test_post_analysis_clause_filter(client: TestClient):
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-003",
            "activity": "food_manufacturing",
            "employee_count": 5,
        },
        "as_at_date": "2024-08-01",
        "clause_ids": ["RULE-CEA-EPL-001"],
    }

    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rules_evaluated"] == 1
    assert data["evaluations"][0]["rule_id"] == "RULE-CEA-EPL-001"
    # CEA requires employee_count >= 20; profile has 5 -> NOT_APPLICABLE
    assert data["evaluations"][0]["status"] == OutcomeStatus.NOT_APPLICABLE.value


# 6. Test POST /analysis with empty body or missing profile
def test_post_analysis_missing_profile(client: TestClient):
    response = client.post("/analysis", json={})
    assert response.status_code == 400
    assert "business profile" in response.json()["detail"].lower()


# 7. Test GET /evaluation/results returns benchmark statistics
def test_get_evaluation_results(client: TestClient):
    response = client.get("/evaluation/results")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "P_Proposed_System" in data["metrics"]
    assert "B0_Oracle_LongContext" in data["metrics"]
    assert "confidence_intervals" in data
    assert "paired_comparisons_vs_system_p" in data


# 8. Test POST /analysis persistent provenance and audit trail
def test_post_analysis_provenance_and_audit_trail(client: TestClient):
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-PROV",
            "activity": "food_manufacturing",
            "employee_count": 30,
            "products": [{"category": "biscuits", "prepackaged": True}],
            "production_capacity": {"value": 100.0, "unit": "kg", "per_period": "day"},
        },
        "as_at_date": "2024-08-01",
        "clause_ids": ["RULE-FCAU-001"],
    }
    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["evaluations"]) >= 1

    ev = data["evaluations"][0]
    assert ev["rule_id"] == "RULE-FCAU-001"
    # Strict persistent provenance fields
    assert ev["document_title"] is not None
    assert ev["page_number"] is not None and ev["page_number"] >= 1
    assert ev["char_start"] is not None and ev["char_start"] >= 0
    assert ev["char_end"] is not None and ev["char_end"] > ev["char_start"]
    assert "APPROVED" in ev["review_status"]
    assert "EXPERT_ADJUDICATOR" in ev["review_status"]
    assert ev["coverage_gap"] is False


# 9. Test POST /analysis coverage gap detection
def test_post_analysis_coverage_gap_unsupported(client: TestClient):
    # Request an unverified or nonexistent clause
    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-GAP",
            "activity": "food_manufacturing",
        },
        "clause_ids": ["CLAUSE-NONEXISTENT-OR-UNAPPROVED-001"],
    }
    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["unsupported_rules_count"] >= 1

    ev = data["evaluations"][0]
    assert ev["status"] == OutcomeStatus.UNSUPPORTED.value
    assert ev["coverage_gap"] is True
    assert "Coverage Gap" in ev["reason"]


# 10. Test app state LLM client initialization and narrative summary generation
def test_app_state_llm_client_initialization(client: TestClient):
    assert hasattr(app.state, "explanation_generator")
    assert app.state.explanation_generator is not None


# 11. Test live LLM explanation generation with mock client
def test_analysis_narrative_summary_generation(client: TestClient, monkeypatch):
    class MockLLMForSummary:
        def generate_text(self, prompt: str) -> str:
            # Return text grounded strictly in facts so EvidenceChecker approves it
            return "As of 2024-08-01, 1 of 2 evaluated regulatory rules apply to your business."

    monkeypatch.setattr(
        app.state,
        "explanation_generator",
        type(app.state.explanation_generator)(llm_client=MockLLMForSummary()),
    )

    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-001",
            "activity": "food_manufacturing",
            "employee_count": 25,
            "products": [{"category": "biscuits", "prepackaged": True}],
            "production_capacity": {"value": 100.0, "unit": "kg", "per_period": "day"},
        },
        "as_at_date": "2024-08-01",
    }
    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["narrative_summary"] == "As of 2024-08-01, 1 of 2 evaluated regulatory rules apply to your business."


# 12. Test Review Queue: GET /admin/reviews
def test_admin_reviews_queue(client: TestClient, db_session):
    from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
    from backend.src.db.session import get_db

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # Ensure parent document exists
        doc = db_session.get(SourceDocumentORM, "doc_fcau_labelling_2024")
        if not doc:
            doc = SourceDocumentORM(
                id="doc_fcau_labelling_2024",
                title="Food (Labelling and Advertising) Regulations 2024",
                authority="Food Control Administration Unit",
                sha256_hash="hash_fcau_test_12345".ljust(64, "0"),
                file_path="backend/data/raw_sources/doc_fcau_labelling_2024.pdf",
                file_size_bytes=1024,
                page_count=1,
                extraction_status="SUCCESS",
            )
            db_session.add(doc)
            db_session.flush()

        # Insert a clause and a pending review rule
        clause = ClauseORM(
            clause_id="CLAUSE-TEST-PENDING-01",
            version_number=1,
            document_id="doc_fcau_labelling_2024",
            clause_number="Regulation 99",
            text="Regulation 99. Synthetic preservatives require special testing certification.",
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=76,
            is_compilable=True,
        )
        db_session.add(clause)
        db_session.flush()

        rule = RuleORM(
            rule_id="RULE-TEST-PENDING-01",
            clause_id="CLAUSE-TEST-PENDING-01",
            clause_version=1,
            outcome_type="STANDARD",
            applies_if={"all": [{"field": "uses_preservatives", "op": "eq", "value": True}]},
            obligation={"type": "testing", "text": "Obtain testing certification."},
            validity={"published": "2024-01-01"},
            source={"clause": "Regulation 99", "quote_span": "Synthetic preservatives require special testing certification."},
            review_status="PENDING_REVIEW",
        )
        db_session.add(rule)
        db_session.commit()

        response = client.get("/admin/reviews")
        assert response.status_code == 200
        reviews = response.json()
        assert isinstance(reviews, list)
        rule_ids = [r["rule_id"] for r in reviews]
        assert "RULE-TEST-PENDING-01" in rule_ids

        matching = next(r for r in reviews if r["rule_id"] == "RULE-TEST-PENDING-01")
        assert matching["review_status"] == "PENDING_REVIEW"
        assert matching["verbatim_quote_span"] == "Synthetic preservatives require special testing certification."
        assert matching["applies_if"]["all"][0]["field"] == "uses_preservatives"
    finally:
        app.dependency_overrides.clear()


# 13. Test Review Queue: POST /admin/reviews/{rule_id}/approve
def test_admin_reviews_approve(client: TestClient, db_session):
    from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
    from backend.src.db.session import get_db

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        doc = db_session.get(SourceDocumentORM, "doc_fcau_labelling_2024")
        if not doc:
            doc = SourceDocumentORM(
                id="doc_fcau_labelling_2024",
                title="Food (Labelling and Advertising) Regulations 2024",
                authority="Food Control Administration Unit",
                sha256_hash="hash_fcau_test_approve".ljust(64, "0"),
                file_path="backend/data/raw_sources/doc_fcau_labelling_2024.pdf",
                file_size_bytes=1024,
                page_count=1,
                extraction_status="SUCCESS",
            )
            db_session.add(doc)
            db_session.flush()

        clause = ClauseORM(
            clause_id="CLAUSE-TEST-APPROVE-01",
            version_number=1,
            document_id="doc_fcau_labelling_2024",
            clause_number="Regulation 101",
            text="Regulation 101. Storage humidity must not exceed 65 percent.",
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=58,
            is_compilable=True,
        )
        db_session.add(clause)
        db_session.flush()

        rule = RuleORM(
            rule_id="RULE-TEST-APPROVE-01",
            clause_id="CLAUSE-TEST-APPROVE-01",
            clause_version=1,
            outcome_type="STANDARD",
            applies_if={"all": [{"field": "warehouse_humidity", "op": "gt", "value": 65}]},
            obligation={"type": "storage", "text": "Maintain storage humidity below 65%"},
            source={"clause": "Regulation 101", "quote_span": "Storage humidity must not exceed 65 percent."},
            review_status="PENDING_REVIEW",
        )
        db_session.add(rule)
        db_session.commit()

        payload = {
            "reviewer_id": "legal_auditor_42",
            "reviewer_role": "PRIMARY_ANNOTATOR",
            "rationale": "Verified quote span and statutory threshold exactly match.",
        }
        response = client.post("/admin/reviews/RULE-TEST-APPROVE-01/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["review_status"] == "APPROVED"

        # Verify database persistence & audit trail
        updated_rule = db_session.get(RuleORM, "RULE-TEST-APPROVE-01")
        assert updated_rule.review_status == "APPROVED"

        audits = db_session.query(HumanReviewAuditORM).filter_by(rule_id="RULE-TEST-APPROVE-01").all()
        assert len(audits) >= 1
        assert audits[-1].reviewer_id == "legal_auditor_42"
        assert audits[-1].decision == "APPROVED"

        # Test 404 for nonexistent rule
        res_404 = client.post("/admin/reviews/NONEXISTENT-RULE/approve", json=payload)
        assert res_404.status_code == 404
    finally:
        app.dependency_overrides.clear()


# 14. Test Review Queue: POST /admin/reviews/{rule_id}/reject
def test_admin_reviews_reject(client: TestClient, db_session):
    from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
    from backend.src.db.session import get_db

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        doc = db_session.get(SourceDocumentORM, "doc_fcau_labelling_2024")
        if not doc:
            doc = SourceDocumentORM(
                id="doc_fcau_labelling_2024",
                title="Food (Labelling and Advertising) Regulations 2024",
                authority="Food Control Administration Unit",
                sha256_hash="hash_fcau_test_reject".ljust(64, "0"),
                file_path="backend/data/raw_sources/doc_fcau_labelling_2024.pdf",
                file_size_bytes=1024,
                page_count=1,
                extraction_status="SUCCESS",
            )
            db_session.add(doc)
            db_session.flush()

        clause = ClauseORM(
            clause_id="CLAUSE-TEST-REJECT-01",
            version_number=1,
            document_id="doc_fcau_labelling_2024",
            clause_number="Regulation 102",
            text="Regulation 102. Ambiguous guideline text.",
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=41,
            is_compilable=True,
        )
        db_session.add(clause)
        db_session.flush()

        rule = RuleORM(
            rule_id="RULE-TEST-REJECT-01",
            clause_id="CLAUSE-TEST-REJECT-01",
            clause_version=1,
            outcome_type="STANDARD",
            applies_if={"all": [{"field": "unknown_metric", "op": "gt", "value": 999}]},
            obligation={"type": "guideline", "text": "Follow ambiguous guideline"},
            source={"clause": "Regulation 102", "quote_span": "Ambiguous guideline text."},
            review_status="PENDING_REVIEW",
        )
        db_session.add(rule)
        db_session.commit()

        payload = {
            "reviewer_id": "legal_auditor_42",
            "reviewer_role": "PRIMARY_ANNOTATOR",
            "rationale": "Hallucinated threshold not supported by statutory text.",
        }
        response = client.post("/admin/reviews/RULE-TEST-REJECT-01/reject", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["review_status"] == "REJECTED"

        updated_rule = db_session.get(RuleORM, "RULE-TEST-REJECT-01")
        assert updated_rule.review_status == "REJECTED"

        audits = db_session.query(HumanReviewAuditORM).filter_by(rule_id="RULE-TEST-REJECT-01").all()
        assert len(audits) >= 1
        assert audits[-1].decision == "REJECTED"
    finally:
        app.dependency_overrides.clear()


# 15. Test Document Upload: POST /admin/documents/upload
def test_admin_document_upload(client: TestClient, tmp_path):
    import pymupdf

    # Create a small valid test PDF
    test_pdf = tmp_path / "test_gazette_upload.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    sample_text = (
        "THE FOOD ACT, No. 26 OF 1980\n\n"
        "Regulation 50. Every commercial cold storage facility operating at temperature below minus 18 degrees Celsius "
        "shall maintain continuous automated digital temperature logging records."
    )
    page.insert_textbox(pymupdf.Rect(50, 50, 545, 792), sample_text, fontsize=11)
    doc.save(str(test_pdf))
    doc.close()

    with open(test_pdf, "rb") as f:
        files = {"file": ("test_gazette_upload.pdf", f, "application/pdf")}
        data = {
            "title": "Food Cold Storage Temperature Regulations 2024",
            "authority": "Food Control Administration Unit",
            "instrument_type": "regulation",
        }
        response = client.post("/admin/documents/upload", files=files, data=data)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["filename"] == "test_gazette_upload.pdf"
    assert res_data["pages_ingested"] >= 1
    assert res_data["clauses_extracted"] >= 1

    # Test non-PDF rejection
    txt_file = {"file": ("invalid.txt", b"plain text", "text/plain")}
    res_bad = client.post("/admin/documents/upload", files=txt_file)
    assert res_bad.status_code == 400


