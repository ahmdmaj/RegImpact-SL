"""Unit tests for Component [C]: LLM-Assisted Rule Compilation (RuleCompiler)."""

from unittest.mock import MagicMock
import pytest

from backend.src.engine.verifier import RuleVerifier
from backend.src.extraction.compiler import (
    LLMClient,
    RuleCompiler,
)
from backend.src.models.domain import Rule


@pytest.fixture
def sample_clause_context():
    """Raw text and metadata for a real Sri Lankan food regulation clause."""
    raw_text = (
        "THE GAZETTE OF THE DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA\n"
        "No. 2024/01 - FRIDAY, JANUARY 01, 2024\n\n"
        "Regulation 4. These regulations may be cited as the Food (Labelling and Packaging) Regulations 2024, "
        "published on 2024-01-01 and shall come into operation on 1st June 2024.\n\n"
        "Every food manufacturing enterprise having a production capacity of 50 kg per day or more, "
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )
    metadata = {
        "instrument": "Food (Labelling and Packaging) Regulations 2024",
        "authority": "FCAU",
        "gazette_no": "2024/01",
        "clause": "Regulation 4",
        "page": 1,
    }
    return raw_text, metadata


@pytest.fixture
def valid_rule_dict():
    """A valid dictionary matching the Rule schema and grounded in sample_clause_context."""
    quote = (
        "published on 2024-01-01 and shall come into operation on 1st June 2024. "
        "Every food manufacturing enterprise having a production capacity of 50 kg per day or more, "
        "and engaged in the production of prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )
    return {
        "rule_id": "RULE-FCAU-COMPILED-001",
        "source": {
            "instrument": "Food (Labelling and Packaging) Regulations 2024",
            "authority": "FCAU",
            "gazette_no": "2024/01",
            "clause": "Regulation 4",
            "page": 1,
            "quote_span": quote,
        },
        "validity": {
            "published": "2024-01-01",
            "commences": "2024-06-01",
            "transition_until": None,
            "superseded_by": None,
        },
        "applies_if": {
            "all": [
                {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                {"field": "products.prepackaged", "op": "eq", "value": True},
                {"field": "production_capacity.kg_per_day", "op": "gte", "value": 50},
            ],
            "any": [],
        },
        "exceptions": [],
        "obligation": {
            "type": "labelling",
            "text": "Display nutrition information panel in Sinhala, Tamil, and English.",
            "impact_categories": ["packaging", "labelling"],
        },
        "verification": {
            "status": "compiled",
            "extraction_model": "mock-llm-v1",
            "agreement": True,
        },
    }


# Test 1 (First-pass success): LLM returns a valid rule on first call
def test_compile_clause_first_pass_success(sample_clause_context, valid_rule_dict):
    raw_text, metadata = sample_clause_context

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.return_value = valid_rule_dict

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    result = compiler.compile_clause(raw_text=raw_text, source_metadata=metadata, max_retries=2)

    assert result is not None
    assert isinstance(result, Rule)
    assert result.rule_id == "RULE-FCAU-COMPILED-001"
    assert result.validity.commences == "2024-06-01"
    assert mock_llm.generate_rule.call_count == 1


# Test 2 (Self-correction success): First call returns hallucinated date, second call fixes it
def test_compile_clause_self_correction_success(sample_clause_context, valid_rule_dict):
    raw_text, metadata = sample_clause_context

    # Create an invalid first attempt where commences is hallucinated to 2025-10-15
    invalid_first_dict = json_copy(valid_rule_dict)
    invalid_first_dict["validity"]["commences"] = "2025-10-15"

    corrected_second_dict = json_copy(valid_rule_dict)

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.side_effect = [invalid_first_dict, corrected_second_dict]

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    result = compiler.compile_clause(raw_text=raw_text, source_metadata=metadata, max_retries=2)

    assert result is not None
    assert isinstance(result, Rule)
    assert result.validity.commences == "2024-06-01"
    assert mock_llm.generate_rule.call_count == 2

    # Verify that the second call's prompt included the verification feedback
    second_call_prompt = mock_llm.generate_rule.call_args_list[1][0][0]
    assert "2025-10-15" in second_call_prompt
    assert "literal_check" in second_call_prompt.lower() or "verification failures" in second_call_prompt.lower()


# Test 3 (Exhausted retries): Repeatedly invalid rule returns None without crashing
def test_compile_clause_exhausted_retries(sample_clause_context, valid_rule_dict):
    raw_text, metadata = sample_clause_context

    # Always return an invalid rule with a hallucinated threshold of 999
    invalid_dict = json_copy(valid_rule_dict)
    invalid_dict["applies_if"]["all"][2]["value"] = 999

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.return_value = invalid_dict

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    # max_retries = 2 means 1 initial attempt + 2 retry attempts = 3 calls
    result = compiler.compile_clause(raw_text=raw_text, source_metadata=metadata, max_retries=2)

    assert result is None
    assert mock_llm.generate_rule.call_count == 3


# Test 4: LLM outputs a valid NON_COMPILABLE rule
def test_compile_clause_non_compilable(sample_clause_context):
    raw_text, metadata = sample_clause_context

    quote = "These regulations may be cited as the Food (Labelling and Packaging) Regulations 2024"
    non_compilable_dict = {
        "rule_id": "RULE-NONCOMP-001",
        "source": {
            "instrument": "Food (Labelling and Packaging) Regulations 2024",
            "authority": "FCAU",
            "gazette_no": "2024/01",
            "clause": "Regulation 4",
            "page": 1,
            "quote_span": quote,
        },
        "validity": {
            "published": "2024-01-01",
            "commences": "2024-06-01",
        },
        "applies_if": {"all": [], "any": []},
        "exceptions": [],
        "obligation": {
            "type": "process",
            "text": "Subjective standard",
            "impact_categories": [],
        },
        "verification": {
            "status": "NON_COMPILABLE",
            "extraction_model": "mock-llm-v1",
            "agreement": True,
            "reason": "Subjective standard without clear numerical boundaries.",
        },
    }

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.return_value = non_compilable_dict

    compiler = RuleCompiler(llm_client=mock_llm)
    result = compiler.compile_clause(raw_text=raw_text, source_metadata=metadata, max_retries=1)

    assert result is not None
    assert result.verification.status == "NON_COMPILABLE"
    assert result.verification.reason == "Subjective standard without clear numerical boundaries."
    assert mock_llm.generate_rule.call_count == 1


# Helper
def json_copy(data: dict) -> dict:
    import json
    return json.loads(json.dumps(data))
