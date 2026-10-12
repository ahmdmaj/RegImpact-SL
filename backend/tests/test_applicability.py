"""Unit tests for the Deterministic Applicability Engine."""

from datetime import date
import pytest

from backend.src.engine.applicability import (
    evaluate_rule,
    evaluate_condition,
    evaluate_temporal_validity,
    extract_field,
    evaluate_operator,
)
from backend.src.models.domain import (
    BusinessProfile,
    Condition,
    AppliesIf,
    EvaluationResult,
    OutcomeStatus,
    Product,
    ProductionCapacity,
    Premises,
    Market,
    Rule,
    Source,
    TriState,
    Validity,
    Verification,
    Obligation,
)


@pytest.fixture
def sample_rule() -> Rule:
    """Fixture providing a standard test rule with conjunction conditions."""
    return Rule(
        rule_id="RULE-FCAU-001",
        source=Source(
            instrument="Food (Labelling and Advertising) Regulations",
            authority="FCAU",
            gazette_no="1234/56",
            clause="Regulation 3(1)",
            page=2,
            quote_span="Every package of food shall carry a label...",
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
            transition_until="2024-12-31",
            superseded_by=None,
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="products.prepackaged", op="eq", value=True),
                Condition(field="production_capacity.kg_per_day", op="gte", value=50),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="labelling",
            text="Provide nutritional panel in English and Sinhala/Tamil.",
            impact_categories=["packaging", "labelling"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="gpt-4o",
            agreement=True,
        ),
    )


@pytest.fixture
def matching_profile() -> BusinessProfile:
    """Fixture providing a profile that completely satisfies sample_rule."""
    return BusinessProfile(
        business_id="BIZ-001",
        activity="food_manufacturing",
        employee_count=15,
        products=[
            Product(category="spices", prepackaged=True)
        ],
        production_capacity=ProductionCapacity(
            value=100.0,
            unit="kg",
            per_period="day",
        ),
        premises=Premises(type="factory", location_authority_area="Kandy"),
        market=Market(domestic=True, import_flag=False, export_flag=False),
        existing_licences=["LIC-01"],
        as_at_date="2024-08-01",
    )


# 1. Full match: Profile satisfies all conditions and date is valid -> APPLICABLE
def test_full_match_applicable(sample_rule: Rule, matching_profile: BusinessProfile):
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    
    assert result.status == OutcomeStatus.APPLICABLE
    assert result.rule_id == "RULE-FCAU-001"
    assert result.missing_fields == []
    assert len(result.evaluation_trace) == 3
    assert all(t["result"] == "TRUE" for t in result.evaluation_trace)
    assert result.temporal_status in ("IN_FORCE", "IN_TRANSITION")


# 2. Explicit mismatch: A condition is explicitly violated -> NOT_APPLICABLE
def test_explicit_mismatch_not_applicable(sample_rule: Rule, matching_profile: BusinessProfile):
    # Alter activity to non-matching
    matching_profile.activity = "textile_manufacturing"
    
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert result.missing_fields == []
    # Trace contains the failing condition
    activity_trace = next(t for t in result.evaluation_trace if t["field"] == "activity")
    assert activity_trace["result"] == "FALSE"
    assert activity_trace["observed_value"] == "textile_manufacturing"


# 3. Missing data: A required condition field is None in the profile -> CONDITIONAL_MISSING_DATA
def test_missing_data_conditional(sample_rule: Rule, matching_profile: BusinessProfile):
    # Set capacity to None
    matching_profile.production_capacity = None
    
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    
    assert result.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "production_capacity.kg_per_day" in result.missing_fields
    capacity_trace = next(t for t in result.evaluation_trace if t["field"] == "production_capacity.kg_per_day")
    assert capacity_trace["result"] == "UNKNOWN"
    assert capacity_trace["observed_value"] is None


# 4. Temporal check: Valid conditions, but as_at_date is prior to commencement date -> NOT_APPLICABLE
def test_temporal_prior_to_commencement(sample_rule: Rule, matching_profile: BusinessProfile):
    # Rule commences 2024-06-01, evaluating on 2024-03-01
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-03-01")
    
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert result.temporal_status == "NOT_YET_IN_FORCE"
    assert "not yet in force" in result.reason.lower()


# 5. Short-circuit safety: Missing (UNKNOWN) + FALSE in AND block -> NOT_APPLICABLE
def test_short_circuit_safety_and_block(sample_rule: Rule, matching_profile: BusinessProfile):
    # One condition is missing (products is None -> UNKNOWN)
    matching_profile.products = None
    # Another condition is explicitly violated (capacity is 20 < 50 -> FALSE)
    matching_profile.production_capacity = ProductionCapacity(
        value=20.0,
        unit="kg",
        per_period="day",
    )
    
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    
    # In Kleene logic: UNKNOWN AND FALSE is FALSE.
    # Because capacity is definitively below threshold, missing product data cannot flip the outcome.
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert result.missing_fields == []


# 6. Temporal check: Superseded rule
def test_temporal_superseded(sample_rule: Rule, matching_profile: BusinessProfile):
    sample_rule.validity.superseded_by = "RULE-FCAU-002"
    sample_rule.validity.superseded_date = "2025-01-01"
    sample_rule.validity.transition_until = None
    
    # As-at date after superseded_date
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2025-06-01")
    assert result.status == OutcomeStatus.NOT_APPLICABLE
    assert result.temporal_status == "SUPERSEDED"


# 7. Temporal check: Transition period grace
def test_temporal_transition_period(sample_rule: Rule, matching_profile: BusinessProfile):
    sample_rule.validity.superseded_by = "RULE-FCAU-002"
    sample_rule.validity.superseded_date = "2025-01-01"
    sample_rule.validity.transition_until = "2025-12-31"
    
    # As-at date during transition period: rule remains in transition
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2025-06-01")
    assert result.status == OutcomeStatus.APPLICABLE
    assert result.temporal_status == "IN_TRANSITION"


# 8. Unsupported / Non-compilable clause handling
def test_unsupported_non_compilable_clause(sample_rule: Rule, matching_profile: BusinessProfile):
    sample_rule.verification.status = "NON_COMPILABLE"
    
    result = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    assert result.status == OutcomeStatus.UNSUPPORTED
    assert "NON_COMPILABLE" in result.reason or "UNSUPPORTED" in result.reason


# 9. Disjunction (OR / any) Kleene logic
def test_or_logic_with_three_valued_evaluation(matching_profile: BusinessProfile):
    rule = Rule(
        rule_id="RULE-OR-TEST",
        source=Source(
            instrument="Environmental Act",
            authority="CEA",
            gazette_no="999",
            clause="Schedule 1",
            page=1,
            quote_span="...",
        ),
        validity=Validity(published="2020-01-01", commences="2020-01-01"),
        applies_if=AppliesIf(
            any=[
                Condition(field="employee_count", op="gte", value=50),  # Profile has 15 -> FALSE
                Condition(field="market.export_flag", op="eq", value=True),  # Profile has False -> FALSE
            ]
        ),
        exceptions=[],
        obligation=Obligation(type="licensing", text="EPL required", impact_categories=["licensing"]),
        verification=Verification(status="human_verified", extraction_model="manual", agreement=True),
    )

    # Both FALSE -> NOT_APPLICABLE
    res1 = evaluate_rule(rule, matching_profile, as_at_date="2024-01-01")
    assert res1.status == OutcomeStatus.NOT_APPLICABLE

    # One TRUE in OR -> APPLICABLE
    matching_profile.employee_count = 60
    res2 = evaluate_rule(rule, matching_profile, as_at_date="2024-01-01")
    assert res2.status == OutcomeStatus.APPLICABLE

    # One UNKNOWN and one FALSE in OR -> CONDITIONAL_MISSING_DATA
    matching_profile.employee_count = 10  # FALSE
    matching_profile.market = None        # UNKNOWN
    res3 = evaluate_rule(rule, matching_profile, as_at_date="2024-01-01")
    assert res3.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "market.export_flag" in res3.missing_fields


# 10. Core operators testing
@pytest.mark.parametrize(
    "op,observed,target,expected",
    [
        ("eq", "food_manufacturing", "FOOD_MANUFACTURING", True),
        ("eq", 50, 50.0, True),
        ("neq", "food_manufacturing", "catering", True),
        ("gt", 55, 50, True),
        ("gt", 50, 50, False),
        ("gte", 50, 50, True),
        ("lt", 15, 20, True),
        ("lte", 20, 20, True),
        ("in", "tea", ["tea", "coffee", "cocoa"], True),
        ("in", "rubber", ["tea", "coffee"], False),
        ("contains", ["EPL_A", "FCAU_REG"], "EPL_A", True),
        ("contains", "Western Province", "Western", True),
    ],
)
def test_operator_evaluation(op, observed, target, expected):
    assert evaluate_operator(op, observed, target) is expected


# 11. Exception handling in rule
def test_rule_exception_handling(sample_rule: Rule, matching_profile: BusinessProfile):
    # Add an exception: cottage industries are exempt
    sample_rule.exceptions = [
        Condition(field="employee_count", op="lte", value=5)
    ]
    
    # Profile has 15 employees -> Exception is FALSE -> Rule is APPLICABLE
    res = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    assert res.status == OutcomeStatus.APPLICABLE

    # Profile has 3 employees -> Exception is TRUE -> Rule is NOT_APPLICABLE
    matching_profile.employee_count = 3
    res_exempt = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    assert res_exempt.status == OutcomeStatus.NOT_APPLICABLE
    assert "exception" in res_exempt.reason.lower()

    # Profile employee_count is None -> Exception is UNKNOWN -> CONDITIONAL_MISSING_DATA
    matching_profile.employee_count = None
    res_unknown = evaluate_rule(sample_rule, matching_profile, as_at_date="2024-08-01")
    assert res_unknown.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "employee_count" in res_unknown.missing_fields
