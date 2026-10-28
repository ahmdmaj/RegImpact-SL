"""Rule extraction and compilation package for RegImpact-SL."""

from backend.src.extraction.compiler import (
    BaseLLMClient,
    CompilationError,
    CompilationResult,
    LLMClient,
    RuleCompiler,
    compute_rule_agreement,
    construct_initial_prompt,
    construct_retry_prompt,
    construct_secondary_prompt,
)

from backend.src.extraction.explanation import (
    ExplanationGenerator,
    construct_explanation_prompt,
)

from backend.src.extraction.ingestion import (
    DocumentIngestionService,
    IngestionResult,
    extract_document_preamble,
    segment_clauses_from_page,
    segment_document_clauses,
)

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
)

from backend.src.extraction.embedding_client import (
    BaseEmbeddingClient,
    GeminiEmbeddingClient,
    MockEmbeddingClient,
    OpenAIEmbeddingClient,
    get_embedding_client,
)

__all__ = [
    "BaseLLMClient",
    "CompilationError",
    "CompilationResult",
    "LLMClient",
    "RuleCompiler",
    "compute_rule_agreement",
    "construct_initial_prompt",
    "construct_retry_prompt",
    "construct_secondary_prompt",
    "ExplanationGenerator",
    "construct_explanation_prompt",
    "DocumentIngestionService",
    "IngestionResult",
    "segment_clauses_from_page",
    "OpenAILLMClient",
    "GeminiLLMClient",
    "MockLLMClient",
    "get_llm_client",
    "LLMClientError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "BaseEmbeddingClient",
    "OpenAIEmbeddingClient",
    "GeminiEmbeddingClient",
    "MockEmbeddingClient",
    "get_embedding_client",
]
