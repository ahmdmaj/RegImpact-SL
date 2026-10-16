"""Rule extraction and compilation package for RegImpact-SL."""

from backend.src.extraction.compiler import (
    BaseLLMClient,
    CompilationError,
    LLMClient,
    RuleCompiler,
    construct_initial_prompt,
    construct_retry_prompt,
)

from backend.src.extraction.explanation import (
    ExplanationGenerator,
    construct_explanation_prompt,
)

from backend.src.extraction.ingestion import (
    DocumentIngestionService,
    IngestionResult,
    segment_clauses_from_page,
)

__all__ = [
    "BaseLLMClient",
    "CompilationError",
    "LLMClient",
    "RuleCompiler",
    "construct_initial_prompt",
    "construct_retry_prompt",
    "ExplanationGenerator",
    "construct_explanation_prompt",
    "DocumentIngestionService",
    "IngestionResult",
    "segment_clauses_from_page",
]
