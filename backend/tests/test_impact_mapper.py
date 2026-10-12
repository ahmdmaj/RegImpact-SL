"""Unit tests for Component [H] (Impact and Action Mapper) and Counterfactuals."""

import pytest
from backend.src.engine.applicability import (
    evaluate_rule,
    generate_counterfactuals,
)
from backend.src.engine.impact_mapper import (
    map_impact,
    BusinessImpact,
    SUPPORTED_OBLIGATION_TYPES,
)
from backend.src.models.domain import (
    AppliesIf,
    BusinessProfile,
    Condition,
    EvaluationResult,
    Market,
    Obligation,
    OutcomeStatus,
    Product,
    ProductionCapacity,
    Rule,
    Source,
    Validity,
    Verification,
)


@pytest.fixture
def base_rule() -> Rule:
    """Fixture providing a base rule for impact mapping."""
    return Rule(
        rule_id="RULE-IMPACT-001",
        source=Source(
            instrument="Food Act No. 26 of 1980 Regulations",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 4",
            page=3,
            quote_span="Every manufacturer of prepackaged food...",
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
            transition_until="2024-12-31",
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
            text="Provide nutritional declarations in Sinhala, Tamil, and English.",
            impact_categories=["packaging", "labelling"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="gpt-4o",
            agreement=True,
        ),
    )


@pytest.fixture
def applicable_profile() -> BusinessProfile:
    """Fixture providing a profile satisfying base_rule."""
    return BusinessProfile(
        business_id="BIZ-001",
        activity="food_manufacturing",
        products=[Product(category="biscuits", prepackaged=True)],
        production_capacity=ProductionCapacity(value=60.0, unit="kg", per_period="day"),
        as_at_date="2024-08-01",
    )


# 1. Test mapping across all bounded obligation categories
@pytest.mark.parametrize("ob_type", SUPPORTED_OBLIGATION_TYPES)
def test_map_impact_across_all_obligation_types(base_rule: Rule, applicable_profile: BusinessProfile, ob_type: str):
    base_rule.obligation.type = ob_type
    base_rule.obligation.text = f"Mandatory compliance with {ob_type} statutory procedures."
    
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.APPLICABLE

    impact = map_impact(base_rule, eval_result)
    assert impact is not None
    assert isinstance(impact, BusinessImpact)
    assert impact.obligation_type == ob_type
    assert len(impact.affected_activities) > 0
    assert len(impact.affected_documents) > 0
    assert len(impact.action_items) > 0
    # Specific obligation text should be captured in action items
    assert any(base_rule.obligation.text in item for item in impact.action_items)
    # Authority should be parameterized in action items
    assert any("FCAU" in item for item in impact.action_items)


# 2. Test timeline note computation (in transition vs standard in force)
def test_timeline_note_in_transition(base_rule: Rule, applicable_profile: BusinessProfile):
    # Within transition period (commences 2024-06-01, transition_until 2024-12-31)
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    impact = map_impact(base_rule, eval_result)
    
    assert impact is not None
    assert impact.timeline_note is not None
    assert "2024-12-31" in impact.timeline_note


def test_timeline_note_standard_in_force(base_rule: Rule, applicable_profile: BusinessProfile):
    # Rule with no transition period
    base_rule.validity.transition_until = None
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    impact = map_impact(base_rule, eval_result)
    
    assert impact is not None
    assert impact.timeline_note is not None
    assert "in force since 2024-06-01" in impact.timeline_note.lower()


# 3. Verify no false positive action items for non-applicable outcomes
def test_no_false_positives_for_not_applicable(base_rule: Rule, applicable_profile: BusinessProfile):
    applicable_profile.activity = "textile_manufacturing"
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.NOT_APPLICABLE
    
    # Must strictly return None
    impact = map_impact(base_rule, eval_result)
    assert impact is None


def test_no_false_positives_for_conditional_missing_data(base_rule: Rule, applicable_profile: BusinessProfile):
    applicable_profile.production_capacity = None
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    
    impact = map_impact(base_rule, eval_result)
    assert impact is None


def test_no_false_positives_for_unsupported_clause(base_rule: Rule, applicable_profile: BusinessProfile):
    base_rule.verification.status = "NON_COMPILABLE"
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.UNSUPPORTED
    
    impact = map_impact(base_rule, eval_result)
    assert impact is None


# 4. Counterfactual Generation: Numerical threshold boundary flip when APPLICABLE
def test_counterfactual_numerical_when_applicable(base_rule: Rule, applicable_profile: BusinessProfile):
    # Capacity is 60 kg/day >= 50 threshold -> APPLICABLE
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.APPLICABLE
    assert len(eval_result.counterfactuals) > 0
    
    # Decisive numerical condition flip statement
    expected_cf = "If production capacity were below 50 kg/day, this obligation would not apply."
    assert expected_cf in eval_result.counterfactuals


# 5. Counterfactual Generation: Numerical threshold boundary flip when NOT_APPLICABLE
def test_counterfactual_numerical_when_not_applicable(base_rule: Rule, applicable_profile: BusinessProfile):
    # Capacity is 30 kg/day < 50 threshold -> NOT_APPLICABLE
    applicable_profile.production_capacity = ProductionCapacity(value=30.0, unit="kg", per_period="day")
    
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.NOT_APPLICABLE
    assert len(eval_result.counterfactuals) > 0
    
    # Decisive failing condition flip statement
    expected_cf = "If production capacity were 50 kg/day or greater, this obligation would apply."
    assert expected_cf in eval_result.counterfactuals


# 6. Counterfactual Generation: Boolean condition flip when APPLICABLE
def test_counterfactual_boolean_when_applicable(base_rule: Rule, applicable_profile: BusinessProfile):
    # products.prepackaged is True -> APPLICABLE
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.APPLICABLE
    
    expected_bool_cf = "If products were not prepackaged, this obligation would not apply."
    assert expected_bool_cf in eval_result.counterfactuals


# 7. Counterfactual Generation: Boolean condition flip when NOT_APPLICABLE
def test_counterfactual_boolean_when_not_applicable(base_rule: Rule, applicable_profile: BusinessProfile):
    # products.prepackaged is False -> NOT_APPLICABLE
    applicable_profile.products = [Product(category="biscuits", prepackaged=False)]
    
    eval_result = evaluate_rule(base_rule, applicable_profile, as_at_date="2024-08-01")
    assert eval_result.status == OutcomeStatus.NOT_APPLICABLE
    
    expected_bool_cf = "If products were prepackaged, this obligation would apply."
    assert expected_bool_cf in eval_result.counterfactuals


# 8. Counterfactual Generation: General boolean flag inversion (e.g., market.export_flag)
def test_counterfactual_general_boolean_flag():
    rule = Rule(
        rule_id="RULE-EXPORT-001",
        source=Source(
            instrument="Export Development Act",
            authority="EDB",
            gazette_no="100/1",
            clause="Section 5",
            page=1,
            quote_span="...",
        ),
        validity=Validity(published="2020-01-01", commences="2020-01-01"),
        applies_if=AppliesIf(
            all=[
                Condition(field="market.export_flag", op="eq", value=True),
            ]
        ),
        obligation=Obligation(type="reporting", text="Export customs returns required.", impact_categories=[]),
        verification=Verification(status="human_verified", extraction_model="manual", agreement=True),
    )

    # When NOT_APPLICABLE because export_flag is False
    profile_domestic = BusinessProfile(market=Market(export_flag=False))
    res_not_app = evaluate_rule(rule, profile_domestic, as_at_date="2024-01-01")
    assert res_not_app.status == OutcomeStatus.NOT_APPLICABLE
    assert "If market.export_flag were True, this obligation would apply." in res_not_app.counterfactuals

    # When APPLICABLE because export_flag is True
    profile_export = BusinessProfile(market=Market(export_flag=True))
    res_app = evaluate_rule(rule, profile_export, as_at_date="2024-01-01")
    assert res_app.status == OutcomeStatus.APPLICABLE
    assert "If market.export_flag were False, this obligation would not apply." in res_app.counterfactuals
