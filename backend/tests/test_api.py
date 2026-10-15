"""Integration tests for FastAPI application layer."""

import pytest
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.models.domain import OutcomeStatus


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a TestClient for FastAPI app."""
    return TestClient(app)


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
