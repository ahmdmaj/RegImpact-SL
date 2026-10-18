"""Milestone 2 opt-in live integration tests for real LLM providers.

These tests connect to real LLM endpoints (OpenAI or Gemini) ONLY if an API
key is explicitly provided in the local environment.

By default, during automated CI/offline runs, these tests are cleanly skipped.
"""

from __future__ import annotations

import os
import pytest

from backend.src.extraction.compiler import RuleCompiler
from backend.src.extraction.llm_client import (
    GeminiLLMClient,
    OpenAILLMClient,
    get_llm_client,
)

HAS_LIVE_KEY = bool(
    os.getenv("RUN_LIVE_LLM_TESTS") == "1"
    and (os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY"))
)


@pytest.mark.skipif(not HAS_LIVE_KEY, reason="Live LLM API key not set in environment.")
def test_live_llm_compilation_roundtrip():
    """Live test compiling a real Sri Lanka gazette clause with real LLM provider."""
    raw_clause = (
        "Regulation 4. Every food manufacturing enterprise having a production "
        "capacity of 50 kg per day or more, and engaged in the production of "
        "prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )
    metadata = {
        "instrument": "Food (Labelling and Advertising) Regulations 2024",
        "authority": "Food Control Administration Unit",
        "gazette_no": "2024/99",
        "clause": "Regulation 4",
        "page": 1,
    }

    client = get_llm_client(allow_mock_fallback=False)
    compiler = RuleCompiler(llm_client=client)

    result = compiler.compile_clause_with_agreement(raw_clause, metadata, max_retries=2)

    assert result.rule is not None
    assert result.rule.source.clause == "Regulation 4"
    assert result.review_status in ("APPROVED", "PENDING_REVIEW")
    assert result.outcome_type in ("STANDARD", "CONDITIONAL_RULE")
