"""Milestone 2 unit tests: LLM client adapters, retries, and credential security.

All tests run completely offline without real network calls or API keys.
Test coverage:
  LLM-001  Secret masking redacts sensitive tokens in logs and strings.
  LLM-002  strip_markdown_code_fence extracts JSON from code blocks.
  LLM-003  OpenAILLMClient raises LLMAuthenticationError when no key is set.
  LLM-004  OpenAILLMClient successful rule generation and schema conformance.
  LLM-005  OpenAILLMClient bounded retries on HTTP 429 rate limit.
  LLM-006  OpenAILLMClient bounded retries on HTTP 500 server error.
  LLM-007  OpenAILLMClient does not retry on HTTP 401 unauthorized.
  LLM-008  OpenAILLMClient timeout raises LLMTimeoutError.
  LLM-009  OpenAILLMClient malformed JSON raises LLMResponseError.
  LLM-010  GeminiLLMClient raises LLMAuthenticationError when no key is set.
  LLM-011  GeminiLLMClient successful rule generation.
  LLM-012  GeminiLLMClient bounded retries on 429.
  LLM-013  MockLLMClient operates offline and records calls.
  LLM-014  get_llm_client factory falls back to MockLLMClient safely.
  LLM-015  API key is never exposed in client string representations.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.src.extraction.llm_client import (
    GeminiLLMClient,
    LLMAuthenticationError,
    LLMClientError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    MockLLMClient,
    OpenAILLMClient,
    get_llm_client,
    mask_secret,
    strip_markdown_code_fence,
)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_llm_001_mask_secret():
    """Secrets must be redacted and never displayed in full."""
    assert mask_secret(None) == "[NOT SET]"
    assert mask_secret("") == "[NOT SET]"
    assert mask_secret("short") == "[REDACTED]"
    assert mask_secret("sk-1234567890abcdef") == "sk-1...cdef"


def test_llm_002_strip_markdown_code_fence():
    """Markdown code fences must be stripped cleanly."""
    json_str = '{"rule_id": "TEST-01"}'
    assert strip_markdown_code_fence(json_str) == json_str

    wrapped_json = f"```json\n{json_str}\n```"
    assert strip_markdown_code_fence(wrapped_json) == json_str

    wrapped_plain = f"```\n{json_str}\n```"
    assert strip_markdown_code_fence(wrapped_plain) == json_str


def test_llm_003_openai_auth_error_without_key(monkeypatch):
    """OpenAILLMClient must fail fast if no API key is provided."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(LLMAuthenticationError) as exc_info:
        OpenAILLMClient()
    assert "OPENAI_API_KEY environment variable is not set" in str(exc_info.value)


def test_llm_004_openai_generate_rule_success():
    """OpenAILLMClient parses valid JSON response on HTTP 200."""
    rule_data = {"rule_id": "TEST-001", "obligation": {"type": "labelling"}}

    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(rule_data)}}]
    }
    mock_client.post.return_value = mock_response

    client = OpenAILLMClient(api_key="sk-test-fake-key-12345", http_client=mock_client)
    result = client.generate_rule("Extract rule", {})

    assert result == rule_data
    mock_client.post.assert_called_once()


def test_llm_005_openai_retry_on_429():
    """OpenAILLMClient retries on HTTP 429 rate limit."""
    mock_client = MagicMock(spec=httpx.Client)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.text = "Rate limit exceeded"

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": '{"success": true}'}}]
    }

    mock_client.post.side_effect = [resp_429, resp_200]

    client = OpenAILLMClient(
        api_key="sk-test-fake-key-12345",
        http_client=mock_client,
        max_retries=2,
        retry_delay_seconds=0.01,
    )
    result = client.generate_rule("Prompt", {})
    assert result == {"success": True}
    assert mock_client.post.call_count == 2


def test_llm_006_openai_retry_on_500():
    """OpenAILLMClient retries on HTTP 500 server error."""
    mock_client = MagicMock(spec=httpx.Client)

    resp_500 = MagicMock(spec=httpx.Response)
    resp_500.status_code = 500
    resp_500.text = "Internal Server Error"

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": '{"success": true}'}}]
    }

    mock_client.post.side_effect = [resp_500, resp_200]

    client = OpenAILLMClient(
        api_key="sk-test-fake-key-12345",
        http_client=mock_client,
        max_retries=2,
        retry_delay_seconds=0.01,
    )
    result = client.generate_rule("Prompt", {})
    assert result == {"success": True}
    assert mock_client.post.call_count == 2


def test_llm_007_openai_no_retry_on_401():
    """OpenAILLMClient does not retry on HTTP 401 authentication error."""
    mock_client = MagicMock(spec=httpx.Client)

    resp_401 = MagicMock(spec=httpx.Response)
    resp_401.status_code = 401
    resp_401.text = "Unauthorized"
    mock_client.post.return_value = resp_401

    client = OpenAILLMClient(
        api_key="sk-test-fake-key-12345",
        http_client=mock_client,
        max_retries=3,
        retry_delay_seconds=0.01,
    )
    with pytest.raises(LLMAuthenticationError):
        client.generate_rule("Prompt", {})

    assert mock_client.post.call_count == 1


def test_llm_008_openai_timeout_handling():
    """OpenAILLMClient raises LLMTimeoutError on timeout."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.TimeoutException("Read timeout")

    client = OpenAILLMClient(
        api_key="sk-test-fake-key-12345",
        http_client=mock_client,
        max_retries=1,
        retry_delay_seconds=0.01,
    )
    with pytest.raises(LLMTimeoutError):
        client.generate_rule("Prompt", {})


def test_llm_009_openai_malformed_json():
    """OpenAILLMClient raises LLMResponseError on malformed JSON content."""
    mock_client = MagicMock(spec=httpx.Client)
    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": "not valid json {"}}]
    }
    mock_client.post.return_value = resp_200

    client = OpenAILLMClient(
        api_key="sk-test-fake-key-12345",
        http_client=mock_client,
        max_retries=0,
    )
    with pytest.raises(LLMResponseError) as exc_info:
        client.generate_rule("Prompt", {})
    assert "malformed JSON" in str(exc_info.value)


def test_llm_010_gemini_auth_error_without_key(monkeypatch):
    """GeminiLLMClient raises LLMAuthenticationError when no key is set."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(LLMAuthenticationError):
        GeminiLLMClient()


def test_llm_011_gemini_generate_rule_success():
    """GeminiLLMClient parses valid Gemini candidate JSON output."""
    mock_client = MagicMock(spec=httpx.Client)
    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": '{"rule_id": "GEMINI-01"}'}]}}
        ]
    }
    mock_client.post.return_value = resp_200

    client = GeminiLLMClient(
        api_key="AIzaSy-fake-gemini-key-12345",
        http_client=mock_client,
    )
    result = client.generate_rule("Prompt", {})
    assert result == {"rule_id": "GEMINI-01"}


def test_llm_012_gemini_retry_on_429():
    """GeminiLLMClient retries on HTTP 429."""
    mock_client = MagicMock(spec=httpx.Client)

    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.text = "Quota exceeded"

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"retried": true}'}]}}]
    }
    mock_client.post.side_effect = [resp_429, resp_200]

    client = GeminiLLMClient(
        api_key="AIzaSy-fake-gemini-key-12345",
        http_client=mock_client,
        max_retries=1,
        retry_delay_seconds=0.01,
    )
    result = client.generate_rule("Prompt", {})
    assert result == {"retried": True}
    assert mock_client.post.call_count == 2


def test_llm_013_mock_llm_client():
    """MockLLMClient generates canned responses and records history."""
    canned = {"rule_id": "MOCK-001"}
    client = MockLLMClient(canned_rule_dict=canned, canned_text="Explanation")

    rule = client.generate_rule("Prompt 1", {})
    assert rule == canned

    text = client.generate_text("Prompt 2")
    assert text == "Explanation"

    assert len(client.call_history) == 2


def test_llm_014_factory_mock_fallback(monkeypatch):
    """get_llm_client safely returns MockLLMClient when no keys exist in test env."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    client = get_llm_client(allow_mock_fallback=True)
    assert isinstance(client, MockLLMClient)


def test_llm_015_key_redaction_in_logs():
    """API key must never appear in logs or string representations."""
    raw_key = "sk-super-secret-production-key-998877"
    client = OpenAILLMClient(api_key=raw_key, http_client=MagicMock())

    assert raw_key not in repr(client)
    assert raw_key not in str(client)
    assert mask_secret(raw_key) == "sk-s...8877"
    assert raw_key not in mask_secret(raw_key)
