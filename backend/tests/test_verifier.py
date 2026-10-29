"""Unit tests for Component [E]: The Verification Pipeline (RuleVerifier)."""

import pytest

from backend.src.engine.verifier import (
    RuleVerifier,
    verify_rule,
    normalize_text,
    number_in_text,
    date_in_text,
    unit_in_text,
)
from backend.src.models.domain import (
    AppliesIf,
    Condition,
    Obligation,
    Rule,
    RuleEvidence,
    Source,
    Validity,
    Verification,
    VerificationReport,
    VerificationIssue,
)


@pytest.fixture
def sample_source_text() -> str:
    """Fixture providing raw text of a Sri Lankan gazette section."""
    return (
        "THE GAZETTE OF THE DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA (EXTRAORDINARY)\n"
        "No. 2024/01 - FRIDAY, JANUARY 01, 2024\n\n"
        "PART I : SECTION (I) - GENERAL\n\n"
        "FOOD ACT, No. 26 OF 1980\n"
        "REGULATIONS made by the Minister of Health under section 32 of the Food Act, No. 26 of 1980.\n\n"
        "Regulation 4. These regulations may be cited as the Food (Labelling and Packaging) Regulations 2024, "
        "published on 2024-01-01 and shall come into operation on 1st June 2024.\n\n"
        "Every food manufacturing enterprise having a production capacity of 50 kg per day or more, "
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )


@pytest.fixture
def valid_rule() -> Rule:
    """Fixture providing a perfectly extracted, fully grounded rule."""
    quote = (
        "published on 2024-01-01 and shall come into operation on 1st June 2024. "
        "Every food manufacturing enterprise having a production capacity of 50 kg per day or more, "
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )
    return Rule(
        rule_id="RULE-FCAU-VALID-001",
        source=Source(
            instrument="Food (Labelling and Packaging) Regulations 2024",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 4",
            page=1,
            quote_span=quote,
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
            transition_until=None,
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
            text="Ensure each retail package carries a nutrition information panel in Sinhala, Tamil, and English.",
            impact_categories=["packaging", "labelling"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="gpt-4o",
            agreement=True,
        ),
    )


# 1. Valid Rule: A perfectly extracted rule passes all stages with is_valid == True
def test_valid_rule_passes_all_stages(valid_rule: Rule, sample_source_text: str):
    verifier = RuleVerifier()
    report = verifier.verify(valid_rule, source_text=sample_source_text)

    assert report.is_valid is True
    assert report.status == "verified"
    assert len([i for i in report.issues if i.severity == "error"]) == 0


# 2. Quote Grounding Failure: A rule where quote_span does not exist in the source document fails Stage 2
def test_quote_grounding_failure(valid_rule: Rule, sample_source_text: str):
    # Substitute hallucinated quote span
    valid_rule.source.quote_span = "All confectionery makers must submit bi-weekly microbiological lab reports."

    report = verify_rule(valid_rule, source_text=sample_source_text)

    assert report.is_valid is False
    assert report.status == "rejected"
    grounding_issues = [i for i in report.issues if i.stage == "quote_grounding"]
    assert len(grounding_issues) > 0
    assert any("not exist verbatim" in i.message.lower() for i in grounding_issues)


# 3. Literal Check Failure: Threshold 50 never appears in quote_span (model hallucinated 50 instead of 100)
def test_literal_check_failure_hallucinated_threshold(valid_rule: Rule, sample_source_text: str):
    # Quote text mentions 100 kg, but rule condition has threshold 50
    modified_source = sample_source_text.replace("50 kg", "100 kg")
    valid_rule.source.quote_span = valid_rule.source.quote_span.replace("50 kg", "100 kg")
    # Condition still expects 50 (hallucinated threshold)
    valid_rule.applies_if.all[2].value = 50

    report = verify_rule(valid_rule, source_text=modified_source)

    assert report.is_valid is False
    assert report.status == "rejected"
    literal_issues = [i for i in report.issues if i.stage == "literal_check"]
    assert len(literal_issues) > 0
    assert any("numeric threshold '50'" in i.message.lower() for i in literal_issues)


# 4. Literal Check Failure: Date never appears in quote_span
def test_literal_check_failure_hallucinated_date(valid_rule: Rule, sample_source_text: str):
    # Condition requires a date that does not exist in quote_span
    valid_rule.applies_if.all.append(
        Condition(field="registered_after", op="gte", value="2025-10-15")
    )

    report = verify_rule(valid_rule, source_text=sample_source_text)

    assert report.is_valid is False
    assert report.status == "rejected"
    literal_issues = [i for i in report.issues if i.stage == "literal_check"]
    assert len(literal_issues) > 0
    assert any("date literal '2025-10-15'" in i.message.lower() for i in literal_issues)


# 5. Non-Compilable Rule: Validates properly formed NON_COMPILABLE status
def test_non_compilable_rule_valid(sample_source_text: str):
    quote = "published on 2024-01-01 and shall come into operation on 1st June 2024."
    rule = Rule(
        rule_id="RULE-FCAU-DISCRETION-001",
        source=Source(
            instrument="Food Act No. 26 of 1980",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 12",
            page=2,
            quote_span=quote,
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
        ),
        applies_if=AppliesIf(all=[], any=[]),
        exceptions=[],
        obligation=Obligation(
            type="process",
            text="Minister may grant exemption based on deemed public interest.",
            impact_categories=[],
        ),
        verification=Verification(
            status="NON_COMPILABLE",
            extraction_model="gpt-4o",
            agreement=True,
            reason="Subjective ministerial discretion ('public interest') cannot be formalised deterministically.",
        ),
    )

    report = verify_rule(rule, source_text=sample_source_text)

    assert report.is_valid is True
    assert report.status == "non_compilable"
    assert len([i for i in report.issues if i.severity == "error"]) == 0


# 6. Non-Compilable Rule: Fails when missing justification reason
def test_non_compilable_missing_justification(sample_source_text: str):
    quote = "published on 2024-01-01 and shall come into operation on 1st June 2024."
    rule = Rule(
        rule_id="RULE-NONCOMP-NO-REASON",
        source=Source(
            instrument="Food Act No. 26 of 1980",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 12",
            page=2,
            quote_span=quote,
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
        ),
        applies_if=AppliesIf(all=[]),
        obligation=Obligation(type="process", text="", impact_categories=[]),
        verification=Verification(
            status="NON_COMPILABLE",
            extraction_model="gpt-4o",
            agreement=True,
            reason="",
        ),
    )

    report = verify_rule(rule, source_text=sample_source_text)

    assert report.is_valid is False
    assert report.status == "rejected"
    assert any("justification reason" in i.message.lower() for i in report.issues)


# 7. Non-Compilable Rule: Fails when leaving half-baked conditions behind
def test_non_compilable_with_half_baked_conditions(sample_source_text: str):
    quote = "published on 2024-01-01 and shall come into operation on 1st June 2024."
    rule = Rule(
        rule_id="RULE-NONCOMP-HALF-BAKED",
        source=Source(
            instrument="Food Act No. 26 of 1980",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 12",
            page=2,
            quote_span=quote,
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
        ),
        applies_if=AppliesIf(
            all=[Condition(field="activity", op="eq", value="food_manufacturing")]
        ),
        obligation=Obligation(type="process", text="Ambiguous clause", impact_categories=[]),
        verification=Verification(
            status="NON_COMPILABLE",
            extraction_model="gpt-4o",
            agreement=True,
            reason="Ambiguous clause.",
        ),
    )

    report = verify_rule(rule, source_text=sample_source_text)

    assert report.is_valid is False
    assert report.status == "rejected"
    assert any("cannot contain executable conditions" in i.message.lower() for i in report.issues)


# 8. Whitespace/Punctuation Resiliency: Newlines and multi-spaces in raw PDF text
def test_whitespace_and_punctuation_resiliency(valid_rule: Rule):
    # Source text containing typical PDF extraction artifacts: line-wraps and double spaces
    dirty_source_text = (
        "THE GAZETTE OF SRI LANKA\n\n"
        "published on 2024-01-01   and shall\ncome into operation on 1st June 2024.\n"
        "Every food manufacturing enterprise\nhaving a production capacity of 50 kg   per day or more,\n"
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries\n"
        "a nutrition information panel in Sinhala, Tamil, and English."
    )

    # Clean single-line quote span in rule
    valid_rule.source.quote_span = (
        "published on 2024-01-01 and shall come into operation on 1st June 2024. "
        "Every food manufacturing enterprise having a production capacity of 50 kg per day or more, "
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )

    report = verify_rule(valid_rule, source_text=dirty_source_text)

    assert report.is_valid is True
    assert report.status == "verified"


# 9. Schema Failure: Unsupported operator rejected
def test_unsupported_operator_fails_stage1(valid_rule: Rule, sample_source_text: str):
    valid_rule.applies_if.all[0].op = "matches_regex"  # Not in supported operators

    report = verify_rule(valid_rule, source_text=sample_source_text)

    assert report.is_valid is False
    schema_issues = [i for i in report.issues if i.stage == "schema"]
    assert len(schema_issues) > 0
    assert any("unsupported operator 'matches_regex'" in i.message.lower() for i in schema_issues)


# 10. Digit Boundary Safety: 50 must not match 150
def test_digit_boundary_safety(valid_rule: Rule):
    # Text mentions 150 kg per day, NOT 50 kg per day
    source_with_150 = (
        "published on 2024-01-01 and shall come into operation on 1st June 2024. "
        "Every food manufacturing enterprise having a production capacity of 150 kg per day or more, "
        "shall register."
    )
    valid_rule.source.quote_span = source_with_150
    # Rule condition requires 50 kg
    valid_rule.applies_if.all = [
        Condition(field="production_capacity.kg_per_day", op="gte", value=50)
    ]

    report = verify_rule(valid_rule, source_text=source_with_150)

    assert report.is_valid is False
    literal_issues = [i for i in report.issues if i.stage == "literal_check"]
    assert any("numeric threshold '50'" in i.message.lower() for i in literal_issues)
