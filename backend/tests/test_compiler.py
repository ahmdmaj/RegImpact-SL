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


# ---------------------------------------------------------------------------
# Context-Aware Rule Compilation Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def context_aware_compilation_setup():
    """Setup for substantive clause with separate Regulation 1 contextual evidence."""
    clause_text = (
        "Regulation 3. Every importer of pre-packaged sugar confectionery shall ensure that the "
        "total sugar content does not exceed 12.0g per 100g of product."
    )
    reg1_text = (
        "1. These regulations may be cited as the Food (Sugar Confectionery) Regulations 2024 "
        "and shall come into operation on 01st July 2026."
    )
    metadata = {
        "instrument": "Food (Sugar Confectionery) Regulations 2024",
        "authority": "FCAU",
        "gazette_no": "2496/03",
        "clause": "Regulation 3",
        "page": 2,
        "published": "2024-05-15",
        "commences": "2026-07-01",
        "regulation_1_text": reg1_text,
        "context_evidence": {
            "regulation_1": reg1_text,
            "commences": "2026-07-01",
            "published": "2024-05-15",
        },
    }
    candidate_dict = {
        "rule_id": "RULE-SUGAR-003",
        "source": {
            "instrument": "Food (Sugar Confectionery) Regulations 2024",
            "authority": "FCAU",
            "gazette_no": "2496/03",
            "clause": "Regulation 3",
            "page": 2,
            "quote_span": "Every importer of pre-packaged sugar confectionery shall ensure that the total sugar content does not exceed 12.0g per 100g of product.",
            "obligation_quote": "Every importer of pre-packaged sugar confectionery shall ensure that the total sugar content does not exceed 12.0g per 100g of product.",
            "commencement_quote": "shall come into operation on 01st July 2026",
            "commencement_clause": "Regulation 1",
            "threshold_quotes": {
                "sugar_content.g_per_100g": "total sugar content does not exceed 12.0g per 100g",
            },
        },
        "validity": {
            "published": "2024-05-15",
            "commences": "2026-07-01",
            "evidence_quote": "shall come into operation on 01st July 2026",
            "evidence_source": "Regulation 1",
        },
        "applies_if": {
            "all": [
                {"field": "sugar_content.g_per_100g", "op": "lte", "value": 12.0},
            ],
            "any": [],
        },
        "exceptions": [],
        "obligation": {
            "type": "MANDATE",
            "text": "Total sugar content must not exceed 12.0g per 100g.",
            "impact_categories": ["labelling", "composition"],
        },
        "verification": {
            "status": "PENDING_REVIEW",
            "extraction_model": "mock-llm-v1",
            "agreement": False,
        },
    }
    return clause_text, metadata, candidate_dict


def test_context_aware_rule_compilation_success(context_aware_compilation_setup):
    """Exit Condition: Genuinely generated candidate rule with separate evidence passes compilation."""
    clause_text, metadata, candidate_dict = context_aware_compilation_setup

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.return_value = candidate_dict

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    rule = compiler.compile_clause(raw_text=clause_text, source_metadata=metadata, max_retries=1)

    assert rule is not None
    assert isinstance(rule, Rule)
    assert rule.validity.commences == "2026-07-01"
    assert rule.source.commencement_clause == "Regulation 1"
    assert "total sugar content does not exceed 12.0g per 100g" in str(rule.source.threshold_quotes)


def test_context_aware_compilation_rejection_contradictory_date(context_aware_compilation_setup):
    """Exit Condition: Candidate rule claiming contradictory commencement date is rejected."""
    clause_text, metadata, candidate_dict = context_aware_compilation_setup

    contradictory_dict = json_copy(candidate_dict)
    contradictory_dict["validity"]["commences"] = "2028-01-01"  # Contradicts 2026-07-01

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.return_value = contradictory_dict

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    rule = compiler.compile_clause(raw_text=clause_text, source_metadata=metadata, max_retries=1)

    # Verification must fail on contradiction and compiler must return None
    assert rule is None
    assert mock_llm.generate_rule.call_count == 2  # initial attempt + 1 retry


def test_context_aware_compilation_rejection_missing_evidence(context_aware_compilation_setup):
    """Exit Condition: Candidate rule claiming date with missing evidence is rejected."""
    clause_text, metadata, candidate_dict = context_aware_compilation_setup

    # Remove contextual evidence so the claimed date is ungrounded
    metadata_no_context = json_copy(metadata)
    metadata_no_context["regulation_1_text"] = ""
    metadata_no_context["context_evidence"] = {}
    metadata_no_context["commences"] = None

    ungrounded_dict = json_copy(candidate_dict)
    ungrounded_dict["validity"]["commences"] = "2028-01-01"
    ungrounded_dict["source"]["commencement_quote"] = None

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.return_value = ungrounded_dict

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    rule = compiler.compile_clause(raw_text=clause_text, source_metadata=metadata_no_context, max_retries=1)

    assert rule is None


def test_context_aware_dual_pass_agreement(context_aware_compilation_setup):
    """Dual-pass cross-agreement succeeds on context-aware candidate rule."""
    clause_text, metadata, candidate_dict = context_aware_compilation_setup

    candidate_pass_b = json_copy(candidate_dict)
    candidate_pass_b["rule_id"] = "RULE-SUGAR-003-B"

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_rule.side_effect = [candidate_dict, candidate_pass_b]

    compiler = RuleCompiler(llm_client=mock_llm, verifier=RuleVerifier())
    result = compiler.compile_clause_with_agreement(
        raw_text=clause_text,
        source_metadata=metadata,
        auto_approve=True,
    )

    assert result.cross_agreement is True
    assert result.review_status == "APPROVED"
    assert result.rule is not None
    assert result.rule.validity.commences == "2026-07-01"
