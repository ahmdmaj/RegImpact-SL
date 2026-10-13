"""Component [C]: LLM-Assisted Rule Compilation for RegImpact-SL.

Orchestrates LLM-based clause extraction into typed Rule schemas with
automated self-correction loops governed by the RuleVerifier.
"""

from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from backend.src.engine.verifier import RuleVerifier
from backend.src.models.domain import (
    Rule,
    VerificationIssue,
    VerificationReport,
)

logger = logging.getLogger(__name__)


class CompilationError(Exception):
    """Raised when rule compilation fails and cannot be resolved."""

    def __init__(self, message: str, report: Optional[VerificationReport] = None):
        super().__init__(message)
        self.report = report


@runtime_checkable
class LLMClient(Protocol):
    """Abstract protocol for an LLM client capable of schema-constrained generation."""

    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured rule dictionary from a prompt and JSON schema."""
        ...


class BaseLLMClient(ABC):
    """Abstract base class for LLM client implementations."""

    @abstractmethod
    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured rule dictionary from a prompt and JSON schema."""
        pass


def construct_initial_prompt(raw_text: str, source_metadata: Dict[str, Any]) -> str:
    """Construct first-pass prompt for LLM rule compilation."""
    metadata_json = json.dumps(source_metadata, indent=2)
    return (
        "You are an expert legal knowledge extraction assistant for RegImpact-SL.\n"
        "Your goal is to convert the following Sri Lankan regulatory clause into a typed, verified Rule JSON.\n\n"
        "### STRICT EXTRACTION RULES:\n"
        "1. Every threshold, measurement unit, condition, and date MUST appear verbatim in raw_text.\n"
        "2. The 'quote_span' field in source MUST be a verbatim excerpt from raw_text grounding the entire rule.\n"
        "3. Do NOT hallucinate or infer numbers or dates that are not in the text.\n"
        "4. If the clause contains subjective, discretionary, or ambiguous language that cannot be safely compiled, "
        "set verification.status to 'NON_COMPILABLE', provide a clear verification.reason, and leave applies_if empty.\n\n"
        f"### SOURCE METADATA:\n{metadata_json}\n\n"
        f"### RAW REGULATORY CLAUSE:\n{raw_text}\n\n"
        "Output a valid JSON object strictly complying with the Rule schema."
    )


def construct_retry_prompt(
    raw_text: str,
    source_metadata: Dict[str, Any],
    failed_rule_dict: Dict[str, Any],
    issues: List[VerificationIssue],
) -> str:
    """Construct self-correction prompt highlighting specific verification errors."""
    error_lines = [
        f"- [{issue.stage.upper()}] {issue.message}"
        for issue in issues
        if issue.severity == "error"
    ]
    issues_formatted = "\n".join(error_lines)
    previous_attempt_json = json.dumps(failed_rule_dict, indent=2)

    return (
        "Your previous rule extraction failed automated deterministic verification.\n"
        "Please correct the errors identified below:\n\n"
        "### VERIFICATION FAILURES:\n"
        f"{issues_formatted}\n\n"
        "### PREVIOUS FAILED CANDIDATE:\n"
        f"{previous_attempt_json}\n\n"
        f"### RAW REGULATORY CLAUSE:\n{raw_text}\n\n"
        "### INSTRUCTIONS FOR CORRECTION:\n"
        "1. Ensure all numeric thresholds and dates appear verbatim in quote_span and match raw_text exactly.\n"
        "2. Ensure quote_span exists word-for-word in the raw text.\n"
        "3. If the clause cannot be safely compiled without hallucinating missing thresholds, "
        "mark it 'NON_COMPILABLE' with an explicit verification.reason.\n\n"
        "Provide the corrected JSON object complying with the Rule schema."
    )


class RuleCompiler:
    """Compiler orchestrating LLM extraction with RuleVerifier self-correction loop."""

    def __init__(
        self,
        llm_client: Union[LLMClient, BaseLLMClient],
        verifier: Optional[RuleVerifier] = None,
    ):
        self.llm_client = llm_client
        self.verifier = verifier or RuleVerifier()

    def compile_clause(
        self,
        raw_text: str,
        source_metadata: Dict[str, Any],
        max_retries: int = 2,
    ) -> Optional[Rule]:
        """Compile a raw regulatory clause into a verified Rule via self-correcting loop.
        
        Args:
            raw_text: Raw textual content of the clause/page.
            source_metadata: Provenance metadata (instrument, authority, gazette_no, clause, page).
            max_retries: Maximum number of correction attempts after initial extraction failure.
            
        Returns:
            A verified Rule object, or None if validation fails after exhausting retries.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Empty raw_text provided to compile_clause.")
            return None

        rule_schema = Rule.model_json_schema()
        current_prompt = construct_initial_prompt(raw_text, source_metadata)
        last_failed_dict: Optional[Dict[str, Any]] = None
        last_report: Optional[VerificationReport] = None

        # Loop: attempt 0 (initial) + max_retries correction rounds
        for attempt in range(max_retries + 1):
            logger.info("Rule compilation attempt %d for clause %s", attempt + 1, source_metadata.get("clause", "UNKNOWN"))

            try:
                candidate_dict = self.llm_client.generate_rule(current_prompt, rule_schema)
            except Exception as e:
                logger.error("LLM generation error on attempt %d: %s", attempt + 1, str(e))
                # Prepare retry prompt for next attempt if available
                last_failed_dict = {}
                issues = [
                    VerificationIssue(
                        stage="schema",
                        severity="error",
                        message=f"LLM call or JSON parsing failed: {str(e)}",
                    )
                ]
                current_prompt = construct_retry_prompt(raw_text, source_metadata, last_failed_dict, issues)
                continue

            # Ensure baseline metadata fields are preserved if omitted by LLM
            if isinstance(candidate_dict, dict):
                src = candidate_dict.setdefault("source", {})
                if isinstance(src, dict):
                    for k, v in source_metadata.items():
                        if k not in src or src[k] is None:
                            src[k] = v

            # Run deterministic verification gatekeeper
            report = self.verifier.verify(candidate_dict, source_text=raw_text)

            if report.is_valid:
                logger.info("Rule successfully compiled and verified on attempt %d: %s", attempt + 1, candidate_dict.get("rule_id"))
                try:
                    return Rule(**candidate_dict)
                except Exception as e:
                    logger.error("Unexpected Pydantic parsing error after verification passed: %s", str(e))
                    return None

            # Attempt failed verification
            last_failed_dict = candidate_dict
            last_report = report
            error_issues = [i for i in report.issues if i.severity == "error"]
            logger.warning(
                "Verification failed on attempt %d (%d errors): %s",
                attempt + 1,
                len(error_issues),
                "; ".join(i.message for i in error_issues),
            )

            # If retries remain, generate self-correction prompt
            if attempt < max_retries:
                current_prompt = construct_retry_prompt(
                    raw_text=raw_text,
                    source_metadata=source_metadata,
                    failed_rule_dict=candidate_dict,
                    issues=error_issues,
                )

        logger.error(
            "Rule compilation exhausted %d retries without passing verification. Rule rejected.",
            max_retries,
        )
        return None
