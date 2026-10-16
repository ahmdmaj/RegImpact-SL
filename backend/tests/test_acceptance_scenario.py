"""End-to-End Acceptance Scenario Test (Alignment Plan Section 6).

Verifies the complete five-stage pipeline:
  Stage 1: Seeded persistent document in PostgreSQL / SQLite repository.
  Stage 2: Segmented clause anchored to document pages with character offsets.
  Stage 3: Compiled rule linked to clause with EXPERT_ADJUDICATOR approval audit log.
  Stage 4: Deterministic 3-valued evaluation via REST API (POST /analysis).
  Stage 5: Traceable verbatim source quotation and provenance verification.
"""

import pytest
from fastapi.testclient import TestClient

from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
from backend.src.db.session import session_scope
from backend.src.main import app
from backend.src.models.domain import OutcomeStatus


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_section_6_first_end_to_end_acceptance_scenario(client: TestClient):
    """Execute Section 6 End-to-End Acceptance Scenario.
    
    Data Path:
      Seed Document -> Extracted Clause -> Retrieved Rule -> Deterministic Analysis -> Traceable Provenance
    """
    # -------------------------------------------------------------------------
    # Stage 1: Seeded Persistent Document
    # -------------------------------------------------------------------------
    with session_scope() as session:
        from backend.src.main import ensure_database_seeded
        ensure_database_seeded(session)
        doc = session.query(SourceDocumentORM).filter_by(id="doc_fcau_labelling_2024").first()
        assert doc is not None, "Stage 1 Failed: Seeded source document not found in persistent store."
        assert "Food (Labelling and Advertising) Regulations" in doc.title
        assert doc.authority == "Food Control Administration Unit (FCAU)"
        assert len(doc.sha256_hash) == 64
        assert doc.page_count >= 1

        # -------------------------------------------------------------------------
        # Stage 2: Segmented Regulatory Clause
        # -------------------------------------------------------------------------
        clause = (
            session.query(ClauseORM)
            .filter(
                ClauseORM.document_id == doc.id,
                ClauseORM.clause_number == "Regulation 4",
            )
            .first()
        )
        assert clause is not None, "Stage 2 Failed: Segmented clause not anchored to persistent document."
        assert clause.start_page == 1
        assert clause.end_page == 1
        assert clause.char_end > clause.char_start
        assert "50 kg per day" in clause.text

        # -------------------------------------------------------------------------
        # Stage 3: Compiled Rule with Adjudication Audit Log
        # -------------------------------------------------------------------------
        rule_orm = session.query(RuleORM).filter_by(rule_id="RULE-FCAU-REG-4").first()
        assert rule_orm is not None, "Stage 3 Failed: Compiled rule not found."
        assert rule_orm.review_status == "APPROVED"

        audit_entry = (
            session.query(HumanReviewAuditORM)
            .filter_by(rule_id=rule_orm.rule_id, decision="APPROVED")
            .first()
        )
        assert audit_entry is not None, "Stage 3 Failed: Human review audit record missing."
        assert audit_entry.reviewer_role == "EXPERT_ADJUDICATOR"

    # -------------------------------------------------------------------------
    # Stage 4: Deterministic API Evaluation (POST /analysis)
    # -------------------------------------------------------------------------
    # Scenario: Small Colombo biscuit manufacturer producing 75 kg/day prepackaged products
    profile_payload = {
        "business_profile": {
            "business_id": "BIZ-SL-ACCEPTANCE-001",
            "activity": "food_manufacturing",
            "industry": "confectionery_and_bakery",
            "employee_count": 18,
            "products": [
                {"category": "biscuits", "prepackaged": True, "product_name": "Ginger Biscuits"}
            ],
            "production_capacity": {
                "value": 75.0,
                "unit": "kg",
                "per_period": "day",
            },
            "premises": {
                "type": "commercial_factory",
                "location_authority_area": "Colombo Municipal Council",
                "province": "Western Province",
            },
            "market": {
                "domestic": True,
                "export_flag": False,
            },
        },
        "as_at_date": "2024-08-01",
    }

    response = client.post("/analysis", json=profile_payload)
    assert response.status_code == 200, f"Stage 4 Failed: API returned {response.status_code}: {response.text}"
    report_data = response.json()

    # Verify overall impact report
    assert report_data["as_at_date"] == "2024-08-01"
    assert report_data["total_rules_evaluated"] >= 2
    assert report_data["applicable_rules_count"] >= 1
    assert len(report_data["action_checklist"]) > 0

    # -------------------------------------------------------------------------
    # Stage 5: Traceable Provenance & Verbatim Source Quotation
    # -------------------------------------------------------------------------
    eval_fcau = next(
        (e for e in report_data["evaluations"] if e["rule_id"] in ("RULE-FCAU-REG-4", "RULE-FCAU-001")),
        None,
    )
    assert eval_fcau is not None, "Stage 5 Failed: Target FCAU rule evaluation missing from report."
    assert eval_fcau["status"] == OutcomeStatus.APPLICABLE.value
    assert eval_fcau["coverage_gap"] is False

    # Strict provenance assertions
    assert "Food (Labelling and Advertising) Regulations" in eval_fcau["document_title"]
    assert eval_fcau["page_number"] == 1
    assert eval_fcau["char_start"] >= 0
    assert eval_fcau["char_end"] > eval_fcau["char_start"]
    assert "APPROVED by EXPERT_ADJUDICATOR" in eval_fcau["review_status"]

    # Verbatim quotation anchor
    assert eval_fcau["quote_span"] is not None
    assert "50 kg per day" in eval_fcau["quote_span"]
    assert "nutrition information panel" in eval_fcau["quote_span"]

    # Verification of deterministic condition trace
    trace = eval_fcau["evaluation_trace"]
    assert len(trace) >= 2
    assert all(step["result"] == "TRUE" for step in trace)

    # Verification of mapped action items
    assert eval_fcau["impact"] is not None
    assert eval_fcau["impact"]["obligation_type"] == "labelling"
    assert len(eval_fcau["impact"]["action_items"]) > 0
