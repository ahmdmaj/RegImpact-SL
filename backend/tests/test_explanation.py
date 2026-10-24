"""Unit tests for Component [I]: Explanation Layer and Component [J]: Evidence Check."""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.src.db.session import session_scope
from backend.src.engine.evidence import EvidenceChecker, EvidenceCheckResult
from backend.src.extraction.compiler import LLMClient
from backend.src.extraction.explanation import (
    ExplanationGenerator,
    construct_explanation_prompt,
)
from backend.src.main import (
    RuleAnalysisDetail,
    StructuredImpactReport,
    app,
)
from backend.src.models.domain import BusinessImpact, OutcomeStatus


@pytest.fixture
def sample_impact_report() -> StructuredImpactReport:
    """Fixture providing a realistic StructuredImpactReport."""
    quote = (
        "published on 2024-01-01 and shall come into operation on 1st June 2024. "
        "Every food manufacturing enterprise having a production capacity of 50 kg per day or more, "
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )
    return StructuredImpactReport(
        as_at_date="2024-08-01",
        total_rules_evaluated=2,
        applicable_rules_count=1,
        conditional_rules_count=0,
        not_applicable_rules_count=1,
        unsupported_rules_count=0,
        missing_fields=[],
        clarifying_questions=[],
        action_checklist=[
            "Ensure packaging displays required trilingual text (Sinhala, Tamil, English).",
            "Update product packaging artwork to reflect nutritional panels.",
        ],
        affected_activities=["Product packaging design and retail artwork finalisation"],
        affected_documents=["Retail product packaging artwork and label specifications"],
        evaluations=[
            RuleAnalysisDetail(
                rule_id="RULE-FCAU-001",
                clause="Regulation 4",
                instrument="Food (Labelling and Advertising) Regulations",
                authority="Food Control Administration Unit (FCAU)",
                status=OutcomeStatus.APPLICABLE,
                temporal_status="IN_FORCE",
                quote_span=quote,
                missing_fields=[],
                counterfactuals=[
                    "If production capacity were below 50 kg/day, this obligation would not apply."
                ],
                evaluation_trace=[
                    {"field": "activity", "target_value": "food_manufacturing", "observed_value": "food_manufacturing", "result": "TRUE"},
                    {"field": "products.prepackaged", "target_value": True, "observed_value": True, "result": "TRUE"},
                    {"field": "production_capacity.kg_per_day", "target_value": 50, "observed_value": 100, "result": "TRUE"},
                ],
                impact=BusinessImpact(
                    obligation_type="labelling",
                    affected_activities=["Product packaging design"],
                    affected_documents=["Retail label artwork"],
                    action_items=[
                        "Ensure packaging displays required trilingual text (Sinhala, Tamil, English)."
                    ],
                    timeline_note="Immediate compliance required (in force since 2024-06-01).",
                ),
            ),
            RuleAnalysisDetail(
                rule_id="RULE-CEA-EPL-001",
                clause="Schedule 1 Part B Item 12",
                instrument="National Environmental Regulations",
                authority="Central Environmental Authority (CEA)",
                status=OutcomeStatus.NOT_APPLICABLE,
                temporal_status="IN_FORCE",
                quote_span="Any industrial activity employing 20 or more persons shall obtain EPL.",
                missing_fields=[],
                counterfactuals=[
                    "If employee count were 20 or greater, this obligation would apply."
                ],
                evaluation_trace=[
                    {"field": "activity", "target_value": "food_manufacturing", "observed_value": "food_manufacturing", "result": "TRUE"},
                    {"field": "employee_count", "target_value": 20, "observed_value": 15, "result": "FALSE"},
                ],
                impact=None,
            ),
        ],
    )


# 1. Test grounded summary passes EvidenceChecker
def test_evidence_checker_passes_grounded_summary(sample_impact_report: StructuredImpactReport):
    # Summary using strictly facts, numbers, and dates present in sample_impact_report
    grounded_summary = (
        "As of 2024-08-01, 1 of 2 evaluated regulations applies to your enterprise. "
        "Under Regulation 4, your production capacity of 100 kg/day exceeds the 50 kg threshold. "
        "You must update retail packaging artwork with trilingual nutrition panels. "
        "Schedule 1 Part B Item 12 does not apply because you employ 15 persons, below the 20 employee threshold."
    )

    checker = EvidenceChecker()
    is_valid = checker.verify_claims(grounded_summary, sample_impact_report)
    assert is_valid is True

    result: EvidenceCheckResult = checker.check_claims(grounded_summary, sample_impact_report)
    assert result.is_valid is True
    assert result.ungrounded_numbers == []
    assert result.ungrounded_dates == []


# 2. Test hallucinated penalty/fine fails EvidenceChecker
def test_evidence_checker_rejects_hallucinated_fine(sample_impact_report: StructuredImpactReport):
    # LLM hallucinates a fine of Rs. 50,000 not present anywhere in the report
    hallucinated_summary = (
        "Under Regulation 4, you must display nutritional panels. "
        "Failure to register will result in an immediate penalty of Rs. 50,000 and possible closure."
    )

    checker = EvidenceChecker()
    is_valid = checker.verify_claims(hallucinated_summary, sample_impact_report)
    assert is_valid is False

    result = checker.check_claims(hallucinated_summary, sample_impact_report)
    assert result.is_valid is False
    assert 50000.0 in result.ungrounded_numbers
    assert "ungrounded numbers" in result.message.lower()


# 3. Test hallucinated deadline date fails EvidenceChecker
def test_evidence_checker_rejects_hallucinated_date(sample_impact_report: StructuredImpactReport):
    # LLM hallucinates a date like 2029-12-31 not in report
    hallucinated_summary = (
        "Regulation 4 applies to your food manufacturing facility. "
        "You must complete all label changes by 2029-12-31 to avoid prosecution."
    )

    checker = EvidenceChecker()
    is_valid = checker.verify_claims(hallucinated_summary, sample_impact_report)
    assert is_valid is False

    result = checker.check_claims(hallucinated_summary, sample_impact_report)
    assert result.is_valid is False
    assert any("2029-12-31" in d for d in result.ungrounded_dates)


# 4. Test ExplanationGenerator prompt construction & LLM invocation
def test_explanation_generator_calls_llm(sample_impact_report: StructuredImpactReport):
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_text.return_value = (
        "As of 2024-08-01, 1 of 2 evaluated rules applies to your business under Regulation 4."
    )

    generator = ExplanationGenerator(llm_client=mock_llm)
    summary = generator.generate_summary(sample_impact_report)

    assert summary == "As of 2024-08-01, 1 of 2 evaluated rules applies to your business under Regulation 4."
    assert mock_llm.generate_text.call_count == 1

    # Verify that the constructed prompt contains constraints
    sent_prompt = mock_llm.generate_text.call_args[0][0]
    assert "STRICT FACTUAL GROUNDING RULES" in sent_prompt
    assert "Regulation 4" in sent_prompt
    assert "2024-08-01" in sent_prompt


# 5. Test ExplanationGenerator deterministic fallback when no LLMClient configured
def test_explanation_generator_fallback(sample_impact_report: StructuredImpactReport):
    generator = ExplanationGenerator(llm_client=None)
    summary = generator.generate_summary(sample_impact_report)

    assert "2024-08-01" in summary
    assert "1 of 2" in summary

    # Verify that the fallback summary passes EvidenceChecker
    checker = EvidenceChecker()
    assert checker.verify_claims(summary, sample_impact_report) is True


# 6. Test API integration with EvidenceChecker verification (clean summary)
def test_api_analysis_with_verified_narrative():
    with session_scope() as session:
        from backend.src.scripts.seed_corpus import seed_regulatory_corpus
        seed_regulatory_corpus(db=session, include_synthetic_fixtures=True)

    client = TestClient(app)

    # Inject mock generator that produces grounded summary
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_text.return_value = (
        "As of 2024-08-01, Regulation 4 applies to your facility with capacity 100 kg per day."
    )
    app.state.explanation_generator = ExplanationGenerator(llm_client=mock_llm)

    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-100",
            "activity": "food_manufacturing",
            "employee_count": 25,
            "products": [{"category": "biscuits", "prepackaged": True}],
            "production_capacity": {"value": 100.0, "unit": "kg", "per_period": "day"},
        },
        "as_at_date": "2024-08-01",
        "clause_ids": ["RULE-FCAU-001"],
    }

    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["narrative_summary"] == "As of 2024-08-01, Regulation 4 applies to your facility with capacity 100 kg per day."


# 7. Test API integration with EvidenceChecker withholding hallucinated narrative
def test_api_analysis_withholds_hallucinated_narrative():
    client = TestClient(app)

    # Inject mock generator that produces hallucinated fine
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_text.return_value = (
        "Regulation 4 applies. You will be fined Rs. 50,000 if not registered by 2030-01-01."
    )
    app.state.explanation_generator = ExplanationGenerator(llm_client=mock_llm)

    payload = {
        "business_profile": {
            "business_id": "BIZ-SL-101",
            "activity": "food_manufacturing",
            "employee_count": 25,
            "products": [{"category": "biscuits", "prepackaged": True}],
            "production_capacity": {"value": 100.0, "unit": "kg", "per_period": "day"},
        },
        "as_at_date": "2024-08-01",
        "clause_ids": ["RULE-FCAU-001"],
    }

    response = client.post("/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Hallucinated narrative must be withheld by EvidenceChecker
    assert "failed verification" in data["narrative_summary"].lower()

    # Reset state
    app.state.explanation_generator = None
