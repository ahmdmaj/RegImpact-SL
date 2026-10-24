"""Component [B]: Embedding client adapters for dense regulatory retrieval.

Provides:
  - BaseEmbeddingClient: abstract base interface.
  - OpenAIEmbeddingClient: concrete adapter for OpenAI text-embedding-3 endpoints.
  - GeminiEmbeddingClient: concrete adapter for Google Gemini text-embedding-004.
  - MockEmbeddingClient: deterministic offline embedding client with word-overlap semantics.
  - get_embedding_client(): factory function resolving credentials and provider.

Security & Architecture:
  1. Credentials read exclusively from environment variables; never hardcoded.
  2. Bounded retries on transient errors with exponential backoff.
  3. Safe offline test double producing unit-normalized dense vectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import logging
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional

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

from backend.src.extraction.llm_client import (
    LLMAuthenticationError,
    LLMClientError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    mask_secret,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base Interface
# ---------------------------------------------------------------------------

class BaseEmbeddingClient(ABC):
    """Abstract interface for dense embedding models."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the output embedding vectors."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string into a normalized dense vector."""
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings into normalized dense vectors."""
        return [self.embed_text(t) for t in texts]


# ---------------------------------------------------------------------------
# OpenAI Embedding Client
# ---------------------------------------------------------------------------

class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """Adapter for OpenAI text-embedding-3 endpoints (or OpenAI-compatible)."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSION = 768

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError("OPENAI_API_KEY environment variable is not set.")

        self.model = model or os.environ.get("EMBEDDING_MODEL") or self.DEFAULT_MODEL
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("LLM_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self._dimension = int(os.environ.get("EMBEDDING_DIMENSION", dimension or self.DEFAULT_DIMENSION))
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", timeout_seconds))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", max_retries))
        self.retry_delay_seconds = retry_delay_seconds
        self._http_client = http_client

        logger.info(
            "Initialised OpenAIEmbeddingClient (model=%s, dim=%d, key=%s)",
            self.model,
            self._dimension,
            mask_secret(self.api_key),
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def _execute_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if self._http_client is not None:
                    response = self._http_client.post(url, json=payload, headers=headers)
                else:
                    with httpx.Client(timeout=httpx.Timeout(self.timeout_seconds)) as client:
                        response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    return response.json()
                if response.status_code in (401, 403):
                    raise LLMAuthenticationError(f"Embedding auth failed (HTTP {response.status_code})")
                if response.status_code == 429:
                    last_error = LLMRateLimitError("Embedding rate limit exceeded (HTTP 429)")
                elif response.status_code >= 500:
                    last_error = LLMResponseError(f"Server error (HTTP {response.status_code})")
                else:
                    raise LLMResponseError(f"Embedding API error (HTTP {response.status_code})")

            except (httpx.TimeoutException, TimeoutError) as exc:
                last_error = LLMTimeoutError(f"Embedding request timed out: {exc}")
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = LLMClientError(f"Network error: {exc}")

            if attempt < self.max_retries:
                backoff = self.retry_delay_seconds * (2 ** attempt)
                time.sleep(backoff)

        raise last_error or LLMClientError("Embedding failed after exhausting retries.")

    def embed_text(self, text: str) -> List[float]:
        results = self.embed_batch([text])
        return results[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        payload: Dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        if "text-embedding-3" in self.model:
            payload["dimensions"] = self._dimension

        data = self._execute_with_retry(payload)
        try:
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]
        except (KeyError, IndexError) as exc:
            raise LLMResponseError(f"Malformed embedding response: {data}") from exc


# ---------------------------------------------------------------------------
# Google Gemini Embedding Client
# ---------------------------------------------------------------------------

class GeminiEmbeddingClient(BaseEmbeddingClient):
    """Adapter for Google Gemini text-embedding-004 REST API."""

    DEFAULT_MODEL = "text-embedding-004"
    DEFAULT_DIMENSION = 768
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 768,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError("GEMINI_API_KEY environment variable is not set.")

        self.model = model or os.environ.get("EMBEDDING_MODEL") or self.DEFAULT_MODEL
        self._dimension = int(os.environ.get("EMBEDDING_DIMENSION", dimension or self.DEFAULT_DIMENSION))
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", timeout_seconds))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", max_retries))
        self.retry_delay_seconds = retry_delay_seconds
        self._http_client = http_client

        logger.info(
            "Initialised GeminiEmbeddingClient (model=%s, dim=%d, key=%s)",
            self.model,
            self._dimension,
            mask_secret(self.api_key),
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        url = self.API_URL_TEMPLATE.format(model=self.model)
        params = {"key": self.api_key}
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if self._http_client is not None:
                    response = self._http_client.post(url, params=params, json=payload)
                else:
                    with httpx.Client(timeout=httpx.Timeout(self.timeout_seconds)) as client:
                        response = client.post(url, params=params, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    return data["embedding"]["values"]
                if response.status_code in (401, 403):
                    raise LLMAuthenticationError(f"Gemini auth failed (HTTP {response.status_code})")
                if response.status_code == 429:
                    last_error = LLMRateLimitError("Gemini rate limit exceeded (HTTP 429)")
                elif response.status_code >= 500:
                    last_error = LLMResponseError(f"Gemini server error (HTTP {response.status_code})")
                else:
                    raise LLMResponseError(f"Gemini error (HTTP {response.status_code})")

            except (httpx.TimeoutException, TimeoutError) as exc:
                last_error = LLMTimeoutError(f"Request timed out: {exc}")
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = LLMClientError(f"Network error: {exc}")

            if attempt < self.max_retries:
                backoff = self.retry_delay_seconds * (2 ** attempt)
                time.sleep(backoff)

        raise last_error or LLMClientError("Gemini embedding failed after retries.")


# ---------------------------------------------------------------------------
# Deterministic Mock Embedding Client (Offline Tests)
# ---------------------------------------------------------------------------

class MockEmbeddingClient(BaseEmbeddingClient):
    """Deterministic, unit-normalized mock embedding client for offline tests.

    Uses word token hashing to ensure that texts with common legal terminology
    (e.g., 'food manufacturing', 'effluent standard', 'epl license') have
    realistic positive cosine similarities.
    """

    def __init__(self, dimension: int = 768) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _token_vector(self, token: str) -> List[float]:
        """Compute a deterministic zero-mean Gaussian vector for a single token."""
        import random
        rng = random.Random(token)
        return [rng.gauss(0.0, 1.0) for _ in range(self._dimension)]

    def embed_text(self, text: str) -> List[float]:
        """Compute normalized dense vector based on text token aggregation."""
        words = re.findall(r"\w+", text.lower())
        if not words:
            # Deterministic baseline unit vector
            val = 1.0 / math.sqrt(self._dimension)
            return [val] * self._dimension

        accum = [0.0] * self._dimension
        for word in words:
            v = self._token_vector(word)
            for i in range(self._dimension):
                accum[i] += v[i]

        # L2-normalize
        norm = math.sqrt(sum(x * x for x in accum)) or 1.0
        return [x / norm for x in accum]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_embedding_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    allow_mock_fallback: bool = True,
) -> BaseEmbeddingClient:
    """Instantiate an embedding client matching environment configuration."""
    resolved_provider = (
        provider
        or os.environ.get("EMBEDDING_PROVIDER")
        or os.environ.get("LLM_PROVIDER")
        or ""
    ).strip().lower()

    if not resolved_provider:
        if os.environ.get("GEMINI_API_KEY"):
            resolved_provider = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            resolved_provider = "openai"
        elif allow_mock_fallback:
            resolved_provider = "mock"
        else:
            raise LLMAuthenticationError(
                "No live embedding credentials configured (GEMINI_API_KEY or OPENAI_API_KEY missing), and allow_mock_fallback=False."
            )

    if resolved_provider == "openai":
        try:
            return OpenAIEmbeddingClient(api_key=api_key)
        except LLMAuthenticationError:
            if allow_mock_fallback:
                logger.warning("No OpenAI key found; falling back to MockEmbeddingClient.")
                return MockEmbeddingClient()
            raise

    elif resolved_provider == "gemini":
        try:
            return GeminiEmbeddingClient(api_key=api_key)
        except LLMAuthenticationError:
            if allow_mock_fallback:
                logger.warning("No Gemini key found; falling back to MockEmbeddingClient.")
                return MockEmbeddingClient()
            raise

    elif resolved_provider == "mock":
        return MockEmbeddingClient()

    else:
        if allow_mock_fallback:
            return MockEmbeddingClient()
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {resolved_provider!r}")
