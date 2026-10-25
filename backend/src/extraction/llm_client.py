"""Component [C]: Concrete LLM client adapters for RegImpact-SL.

Provides:
  - LLMClientError hierarchy (Authentication, RateLimit, Timeout, Response).
  - OpenAILLMClient: adapter for OpenAI and OpenAI-compatible endpoints.
  - GeminiLLMClient: adapter for Google Gemini REST API.
  - MockLLMClient: in-memory mock client for offline tests.
  - get_llm_client(): factory function resolving credentials and provider.

Constraints (§2, §10 of alignment plan):
  1. Credentials read exclusively from environment variables; never hardcoded.
  2. API keys are strictly redacted in logs, exceptions, and string representations.
  3. Bounded retries with exponential backoff on transient errors (429, 5xx, timeouts).
  4. Safe JSON decoding handling markdown code fences and malformed responses.
  5. Model metadata logged for reproducibility.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import httpx

try:
    from dotenv import load_dotenv
    for _p in [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]:
        if _p.exists():
            load_dotenv(_p, override=False)
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class LLMClientError(Exception):
    """Base exception for all LLM client errors."""
    pass


class LLMAuthenticationError(LLMClientError):
    """Raised when authentication fails (HTTP 401/403 or missing API key)."""
    pass


class LLMRateLimitError(LLMClientError):
    """Raised when rate limits are exceeded (HTTP 429)."""
    pass


class LLMTimeoutError(LLMClientError):
    """Raised when an API request times out."""
    pass


class LLMResponseError(LLMClientError):
    """Raised when the LLM returns an invalid or malformed response."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mask_secret(secret: Optional[str]) -> str:
    """Return a masked representation of a sensitive string for safe logging."""
    if not secret:
        return "[NOT SET]"
    if len(secret) <= 8:
        return "[REDACTED]"
    return f"{secret[:4]}...{secret[-4:]}"


def strip_markdown_code_fence(text: str) -> str:
    """Remove leading/trailing markdown code fences (e.g. ```json ... ```)."""
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


# ---------------------------------------------------------------------------
# Base Interface
# ---------------------------------------------------------------------------

class BaseLLMClient(ABC):
    """Abstract base class for LLM client adapters."""

    @abstractmethod
    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured rule dictionary complying with the given JSON schema."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Generate a free-form natural language completion."""
        pass


# ---------------------------------------------------------------------------
# OpenAI & OpenAI-Compatible Client
# ---------------------------------------------------------------------------

class OpenAILLMClient(BaseLLMClient):
    """Adapter for OpenAI and OpenAI-compatible REST endpoints.

    Supports custom base URLs (e.g., OpenRouter, vLLM, Ollama, Groq).
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError(
                "OPENAI_API_KEY environment variable is not set. "
                "Set OPENAI_API_KEY or LLM_API_KEY to use OpenAILLMClient."
            )

        self.model = model or os.environ.get("LLM_MODEL") or self.DEFAULT_MODEL
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("LLM_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", temperature))
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", timeout_seconds))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", max_retries))
        self.retry_delay_seconds = retry_delay_seconds
        self._http_client = http_client

        logger.info(
            "Initialised OpenAILLMClient (model=%s, base_url=%s, key=%s, temp=%.2f, timeout=%.1fs)",
            self.model,
            self.base_url,
            mask_secret(self.api_key),
            self.temperature,
            self.timeout_seconds,
        )

    def __repr__(self) -> str:
        return f"<OpenAILLMClient model={self.model!r} base_url={self.base_url!r} key={mask_secret(self.api_key)}>"

    def __str__(self) -> str:
        return self.__repr__()

    def _get_client(self) -> httpx.Client:
        if self._http_client is not None:
            return self._http_client
        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def _execute_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request with bounded retries on transient errors."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                # If a custom client was provided, use it; otherwise create scoped client
                if self._http_client is not None:
                    response = self._http_client.post(url, json=payload, headers=headers)
                else:
                    with httpx.Client(timeout=httpx.Timeout(self.timeout_seconds)) as client:
                        response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    return response.json()

                if response.status_code in (401, 403):
                    raise LLMAuthenticationError(
                        f"Authentication failed (HTTP {response.status_code}): {response.text}"
                    )

                if response.status_code == 429:
                    last_error = LLMRateLimitError(
                        f"Rate limit exceeded (HTTP 429): {response.text}"
                    )
                elif response.status_code >= 500:
                    last_error = LLMResponseError(
                        f"Server error from LLM provider (HTTP {response.status_code}): {response.text}"
                    )
                else:
                    raise LLMResponseError(
                        f"Unexpected error from LLM provider (HTTP {response.status_code}): {response.text}"
                    )

            except (httpx.TimeoutException, TimeoutError) as exc:
                last_error = LLMTimeoutError(f"Request timed out after {self.timeout_seconds}s: {exc}")
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = LLMClientError(f"Network connection failed: {exc}")

            if attempt < self.max_retries:
                backoff = self.retry_delay_seconds * (2 ** attempt)
                logger.warning(
                    "OpenAI request attempt %d failed (%s). Retrying in %.2fs...",
                    attempt + 1,
                    last_error,
                    backoff,
                )
                time.sleep(backoff)

        raise last_error or LLMClientError("Request failed after exhausting retries.")

    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured rule JSON."""
        system_instruction = (
            "You are a regulatory extraction assistant for Sri Lanka legislation. "
            "You must return ONLY a valid JSON object complying with the required schema. "
            "Never include markdown formatting, thought tags, or commentary outside the JSON."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        data = self._execute_with_retry(payload)
        try:
            raw_content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMResponseError(f"Unexpected response structure: {data}") from exc

        cleaned = strip_markdown_code_fence(raw_content)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"LLM returned malformed JSON: {exc}. Content snippet: {cleaned[:200]}"
            ) from exc

    def generate_text(self, prompt: str) -> str:
        """Generate free-form text completion."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        data = self._execute_with_retry(payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise LLMResponseError(f"Unexpected response structure: {data}") from exc


# ---------------------------------------------------------------------------
# Google Gemini Client
# ---------------------------------------------------------------------------

class GeminiLLMClient(BaseLLMClient):
    """Adapter for Google Gemini REST API (v1beta generateContent)."""

    DEFAULT_MODEL = "gemini-2.5-flash-lite"
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError(
                "GEMINI_API_KEY environment variable is not set. "
                "Set GEMINI_API_KEY or LLM_API_KEY to use GeminiLLMClient."
            )

        self.model = model or os.environ.get("LLM_MODEL") or self.DEFAULT_MODEL
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", temperature))
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", timeout_seconds))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", max_retries))
        self.retry_delay_seconds = retry_delay_seconds
        self._http_client = http_client

        logger.info(
            "Initialised GeminiLLMClient (model=%s, key=%s, temp=%.2f, timeout=%.1fs)",
            self.model,
            mask_secret(self.api_key),
            self.temperature,
            self.timeout_seconds,
        )

    def __repr__(self) -> str:
        return f"<GeminiLLMClient model={self.model!r} key={mask_secret(self.api_key)}>"

    def __str__(self) -> str:
        return self.__repr__()

    def _execute_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request with bounded retries."""
        url = self.API_URL_TEMPLATE.format(model=self.model)
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if self._http_client is not None:
                    response = self._http_client.post(url, params=params, json=payload, headers=headers)
                else:
                    with httpx.Client(timeout=httpx.Timeout(self.timeout_seconds)) as client:
                        response = client.post(url, params=params, json=payload, headers=headers)

                if response.status_code == 200:
                    return response.json()

                if response.status_code in (401, 403):
                    raise LLMAuthenticationError(
                        f"Gemini authentication failed (HTTP {response.status_code}): {response.text}"
                    )

                if response.status_code == 429:
                    last_error = LLMRateLimitError(
                        f"Gemini rate limit exceeded (HTTP 429): {response.text}"
                    )
                elif response.status_code >= 500:
                    last_error = LLMResponseError(
                        f"Gemini server error (HTTP {response.status_code}): {response.text}"
                    )
                else:
                    raise LLMResponseError(
                        f"Gemini request failed (HTTP {response.status_code}): {response.text}"
                    )

            except (httpx.TimeoutException, TimeoutError) as exc:
                last_error = LLMTimeoutError(f"Gemini request timed out: {exc}")
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = LLMClientError(f"Network connection failed: {exc}")

            if attempt < self.max_retries:
                backoff = self.retry_delay_seconds * (2 ** attempt)
                logger.warning(
                    "Gemini request attempt %d failed (%s). Retrying in %.2fs...",
                    attempt + 1,
                    last_error,
                    backoff,
                )
                time.sleep(backoff)

        raise last_error or LLMClientError("Gemini request failed after exhausting retries.")

    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured rule JSON using Gemini response_mime_type."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "response_mime_type": "application/json",
            },
        }
        data = self._execute_with_retry(payload)
        try:
            candidates = data.get("candidates", [])
            text_content = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMResponseError(f"Unexpected Gemini response structure: {data}") from exc

        cleaned = strip_markdown_code_fence(text_content)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"Gemini returned malformed JSON: {exc}. Content snippet: {cleaned[:200]}"
            ) from exc

    def generate_text(self, prompt: str) -> str:
        """Generate natural language text completion."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
            },
        }
        data = self._execute_with_retry(payload)
        try:
            candidates = data.get("candidates", [])
            return candidates[0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise LLMResponseError(f"Unexpected Gemini response structure: {data}") from exc


# ---------------------------------------------------------------------------
# Mock Client for Offline Tests & Local Development
# ---------------------------------------------------------------------------

class MockLLMClient(BaseLLMClient):
    """Deterministic mock client returning canned or configured outputs.

    Ensures the test suite runs completely offline with no network or API keys.
    """

    def __init__(
        self,
        canned_rule_dict: Optional[Dict[str, Any]] = None,
        canned_text: str = "Mock generated text explanation.",
        error_to_raise: Optional[Exception] = None,
    ) -> None:
        self.canned_rule_dict = canned_rule_dict or {}
        self.canned_text = canned_text
        self.error_to_raise = error_to_raise
        self.call_history: List[Dict[str, Any]] = []

    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        self.call_history.append({"prompt": prompt, "schema": schema, "mode": "rule"})
        if self.error_to_raise:
            raise self.error_to_raise
        return dict(self.canned_rule_dict)

    def generate_text(self, prompt: str) -> str:
        self.call_history.append({"prompt": prompt, "mode": "text"})
        if self.error_to_raise:
            raise self.error_to_raise
        return self.canned_text


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    allow_mock_fallback: bool = True,
) -> BaseLLMClient:
    """Instantiate an LLMClient based on configuration.

    Resolution order for provider:
      1. Explicit `provider` argument.
      2. `LLM_PROVIDER` environment variable.
      3. Auto-detected from available API keys (`GEMINI_API_KEY` -> gemini,
         `OPENAI_API_KEY` -> openai).
      4. `MockLLMClient` if `allow_mock_fallback` is True and no credentials exist.
    """
    resolved_provider = (provider or os.environ.get("LLM_PROVIDER", "")).strip().lower()

    if not resolved_provider:
        if os.environ.get("GEMINI_API_KEY"):
            resolved_provider = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            resolved_provider = "openai"
        elif allow_mock_fallback:
            resolved_provider = "mock"
        else:
            resolved_provider = "openai"

    if resolved_provider == "openai":
        try:
            return OpenAILLMClient(api_key=api_key, model=model)
        except LLMAuthenticationError:
            if allow_mock_fallback:
                logger.warning("No OpenAI key found; falling back to MockLLMClient.")
                return MockLLMClient()
            raise

    elif resolved_provider == "gemini":
        try:
            return GeminiLLMClient(api_key=api_key, model=model)
        except LLMAuthenticationError:
            if allow_mock_fallback:
                logger.warning("No Gemini key found; falling back to MockLLMClient.")
                return MockLLMClient()
            raise

    elif resolved_provider == "mock":
        if not allow_mock_fallback:
            raise LLMAuthenticationError(
                "Mock LLM provider requested or configured, but allow_mock_fallback=False."
            )
        return MockLLMClient()

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {resolved_provider!r}. "
            "Supported values: 'openai', 'gemini', 'mock'."
        )
