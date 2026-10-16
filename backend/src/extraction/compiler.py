"""Component [C]: LLM-Assisted Rule Compilation for RegImpact-SL.

Orchestrates LLM-based clause extraction into typed Rule schemas with:
  1. Automated self-correction loops governed by RuleVerifier.
  2. Dual-pass cross-extraction agreement checking (v4 §8.2, change plan Milestone 2).
  3. Semantic logic comparison preventing auto-approval when passes disagree.
  4. Support for CONDITIONAL_RULE outcomes for unresolved statutory preconditions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple, Union, runtime_checkable

from backend.src.engine.verifier import RuleVerifier
from backend.src.models.domain import (
    Condition,
    Rule,
    VerificationIssue,
    VerificationReport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Operator Normalization for Semantic Agreement Comparison
# ---------------------------------------------------------------------------

OPERATOR_NORMALIZATION: Dict[str, str] = {
    ">=": "gte",
    "<=": "lte",
    ">": "gt",
    "<": "lt",
    "==": "eq",
    "!=": "neq",
    "gte": "gte",
    "lte": "lte",
    "gt": "gt",
    "lt": "lt",
    "eq": "eq",
    "neq": "neq",
    "in": "in",
    "contains": "contains",
}


def normalize_op(op: str) -> str:
    """Normalize operator string to canonical token (e.g. '>=' -> 'gte')."""
    return OPERATOR_NORMALIZATION.get(op.strip().lower(), op.strip().lower())


def normalize_val(val: Any) -> Any:
    """Normalize numeric/string values for comparison (e.g. 50.0 == 50, trimmed strings)."""
    if isinstance(val, (int, float)):
        # If integer equivalent, treat as float for numeric tolerance
        return float(val)
    if isinstance(val, str):
        return val.strip().lower()
    return val


# ---------------------------------------------------------------------------
# Exceptions & Protocols
# ---------------------------------------------------------------------------

class CompilationError(Exception):
    """Raised when rule compilation fails and cannot be resolved."""

    def __init__(self, message: str, report: Optional[VerificationReport] = None):
        super().__init__(message)
        self.report = report


@runtime_checkable
class LLMClient(Protocol):
    """Abstract protocol for an LLM client capable of schema-constrained generation and text completion."""

    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured rule dictionary from a prompt and JSON schema."""
        ...

    def generate_text(self, prompt: str) -> str:
        """Generate a natural language text completion from a prompt."""
        ...


class BaseLLMClient(ABC):
    """Abstract base class for LLM client implementations."""

    @abstractmethod
    def generate_rule(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured rule dictionary from a prompt and JSON schema."""
        pass

    def generate_text(self, prompt: str) -> str:
        """Generate a natural language text completion from a prompt."""
        pass


from backend.src.extraction.llm_client import MockLLMClient  # noqa: E402


# ---------------------------------------------------------------------------
# Prompt Construction
# ---------------------------------------------------------------------------

def construct_initial_prompt(raw_text: str, source_metadata: Dict[str, Any]) -> str:
    """Construct first-pass prompt for LLM rule compilation (literal extraction)."""
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


def construct_secondary_prompt(raw_text: str, source_metadata: Dict[str, Any]) -> str:
    """Construct second-pass prompt for cross-extraction agreement (structural decomposition)."""
    metadata_json = json.dumps(source_metadata, indent=2)
    return (
        "You are an independent regulatory compliance auditor evaluating Sri Lankan legislation.\n"
        "Perform a rigorous structural decomposition of the regulatory clause below into a formal Rule schema.\n\n"
        "### STRUCTURAL AUDIT GUIDELINES:\n"
        "1. Deconstruct all statutory predicates: identify activity, production capacity, threshold limits, and premises.\n"
        "2. Use standard condition operators: 'eq', 'gte', 'lte', 'gt', 'lt', 'in'.\n"
        "3. Ensure the 'quote_span' is an exact literal excerpt from the text that legally justifies the rule.\n"
        "4. If statutory applicability depends on subjective criteria or discretionary administrative conditions, "
        "mark verification.status as 'CONDITIONAL_RULE' or 'NON_COMPILABLE'.\n"
        "5. Output valid JSON only, complying with the Rule schema.\n\n"
        f"### SOURCE CONTEXT:\n{metadata_json}\n\n"
        f"### CLAUSE TEXT:\n{raw_text}\n\n"
        "Output the formal Rule JSON:"
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


# ---------------------------------------------------------------------------
# Semantic Rule Agreement Logic
# ---------------------------------------------------------------------------

def _extract_conditions_set(rule: Union[Rule, Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
    """Extract a normalized set of (field, operator, string_val) tuples from applies_if."""
    if isinstance(rule, Rule):
        ai = rule.applies_if
        all_conds = ai.all or []
        any_conds = ai.any or []
    else:
        ai_dict = rule.get("applies_if", {})
        all_conds = [
            Condition(field=c["field"], op=c["op"], value=c["value"])
            for c in (ai_dict.get("all") or [])
            if isinstance(c, dict) and "field" in c
        ]
        any_conds = [
            Condition(field=c["field"], op=c["op"], value=c["value"])
            for c in (ai_dict.get("any") or [])
            if isinstance(c, dict) and "field" in c
        ]

    result: Set[Tuple[str, str, str]] = set()
    for c in (all_conds + any_conds):
        field_norm = str(c.field).strip().lower()
        op_norm = normalize_op(str(c.op))
        val_norm = str(normalize_val(c.value))
        result.add((field_norm, op_norm, val_norm))
    return result


def compute_rule_agreement(
    rule1: Union[Rule, Dict[str, Any]],
    rule2: Union[Rule, Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """Compare two candidate rules for semantic and logical equivalence.

    Checks:
      1. Condition predicates: fields, normalized operators, and numeric/string thresholds.
      2. Obligation: obligation type and impact categories.
      3. Validity: commences and published dates.
      4. Exceptions presence.

    Returns:
      (agreed: bool, discrepancies: List[str])
    """
    discrepancies: List[str] = []

    # 1. Condition Predicates
    conds1 = _extract_conditions_set(rule1)
    conds2 = _extract_conditions_set(rule2)

    only_in_1 = conds1 - conds2
    only_in_2 = conds2 - conds1

    if only_in_1 or only_in_2:
        diff_msgs = []
        if only_in_1:
            diff_msgs.append(f"Pass A conditions not in Pass B: {sorted(only_in_1)}")
        if only_in_2:
            diff_msgs.append(f"Pass B conditions not in Pass A: {sorted(only_in_2)}")
        discrepancies.append("; ".join(diff_msgs))

    # 2. Obligation
    if isinstance(rule1, Rule):
        obl1_type = rule1.obligation.type.strip().lower()
        obl1_cats = set(c.strip().lower() for c in (rule1.obligation.impact_categories or []))
    else:
        obl1_dict = rule1.get("obligation", {})
        obl1_type = str(obl1_dict.get("type", "")).strip().lower()
        obl1_cats = set(str(c).strip().lower() for c in (obl1_dict.get("impact_categories") or []))

    if isinstance(rule2, Rule):
        obl2_type = rule2.obligation.type.strip().lower()
        obl2_cats = set(c.strip().lower() for c in (rule2.obligation.impact_categories or []))
    else:
        obl2_dict = rule2.get("obligation", {})
        obl2_type = str(obl2_dict.get("type", "")).strip().lower()
        obl2_cats = set(str(c).strip().lower() for c in (obl2_dict.get("impact_categories") or []))

    if obl1_type != obl2_type:
        discrepancies.append(
            f"Obligation type mismatch: Pass A has {obl1_type!r}, Pass B has {obl2_type!r}"
        )

    if obl1_cats != obl2_cats:
        discrepancies.append(
            f"Impact categories mismatch: Pass A={sorted(obl1_cats)}, Pass B={sorted(obl2_cats)}"
        )

    # 3. Validity (commences date is critical)
    if isinstance(rule1, Rule):
        commences1 = str(rule1.validity.commences).strip()
    else:
        commences1 = str(rule1.get("validity", {}).get("commences", "")).strip()

    if isinstance(rule2, Rule):
        commences2 = str(rule2.validity.commences).strip()
    else:
        commences2 = str(rule2.get("validity", {}).get("commences", "")).strip()

    if commences1 and commences2 and commences1 != commences2:
        discrepancies.append(
            f"Commencement date mismatch: Pass A has {commences1!r}, Pass B has {commences2!r}"
        )

    agreed = len(discrepancies) == 0
    return agreed, discrepancies


# ---------------------------------------------------------------------------
# Compilation Result Dataclass
# ---------------------------------------------------------------------------

@dataclass
class CompilationResult:
    """Outcome of a rule compilation with cross-extraction agreement."""
    rule: Optional[Rule]
    secondary_rule: Optional[Rule]
    cross_agreement: bool
    review_status: str  # "APPROVED" | "PENDING_REVIEW" | "NON_COMPILABLE" | "REJECTED"
    outcome_type: str   # "STANDARD" | "CONDITIONAL_RULE"
    discrepancies: List[str] = field(default_factory=list)
    verification_report: Optional[VerificationReport] = None


# ---------------------------------------------------------------------------
# Rule Compiler
# ---------------------------------------------------------------------------

class RuleCompiler:
    """Compiler orchestrating LLM extraction with RuleVerifier self-correction loop

    and dual-pass cross-extraction agreement (Milestone 2).
    """

    def __init__(
        self,
        llm_client: Union[LLMClient, BaseLLMClient],
        verifier: Optional[RuleVerifier] = None,
    ):
        self.llm_client = llm_client
        self.verifier = verifier or RuleVerifier()

    def _extract_single_pass(
        self,
        raw_text: str,
        source_metadata: Dict[str, Any],
        prompt_generator,
        client: Union[LLMClient, BaseLLMClient],
        max_retries: int = 2,
    ) -> Tuple[Optional[Rule], Optional[VerificationReport]]:
        """Run a single extraction pass with self-correction retry loop."""
        rule_schema = Rule.model_json_schema()
        current_prompt = prompt_generator(raw_text, source_metadata)
        last_report: Optional[VerificationReport] = None

        for attempt in range(max_retries + 1):
            try:
                candidate_dict = client.generate_rule(current_prompt, rule_schema)
            except Exception as e:
                logger.error("LLM generation error on attempt %d: %s", attempt + 1, str(e))
                issues = [
                    VerificationIssue(
                        stage="schema",
                        severity="error",
                        message=f"LLM call or JSON parsing failed: {str(e)}",
                    )
                ]
                current_prompt = construct_retry_prompt(raw_text, source_metadata, {}, issues)
                continue

            # Ensure baseline metadata fields are preserved
            if isinstance(candidate_dict, dict):
                src = candidate_dict.setdefault("source", {})
                if isinstance(src, dict):
                    for k, v in source_metadata.items():
                        if k not in src or src[k] is None:
                            src[k] = v

            # Deterministic verification gatekeeper
            report = self.verifier.verify(candidate_dict, source_text=raw_text)
            last_report = report

            if report.is_valid:
                try:
                    return Rule(**candidate_dict), report
                except Exception as e:
                    logger.error("Pydantic parsing error after verification passed: %s", str(e))
                    return None, report

            error_issues = [i for i in report.issues if i.severity == "error"]
            if attempt < max_retries:
                current_prompt = construct_retry_prompt(
                    raw_text=raw_text,
                    source_metadata=source_metadata,
                    failed_rule_dict=candidate_dict,
                    issues=error_issues,
                )

        return None, last_report

    def compile_clause(
        self,
        raw_text: str,
        source_metadata: Dict[str, Any],
        max_retries: int = 2,
    ) -> Optional[Rule]:
        """Compile a raw regulatory clause into a verified Rule via self-correcting loop.

        Maintains full backward compatibility for existing callers and Phase A unit tests.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Empty raw_text provided to compile_clause.")
            return None

        rule, _ = self._extract_single_pass(
            raw_text=raw_text,
            source_metadata=source_metadata,
            prompt_generator=construct_initial_prompt,
            client=self.llm_client,
            max_retries=max_retries,
        )
        return rule

    def compile_clause_with_agreement(
        self,
        raw_text: str,
        source_metadata: Dict[str, Any],
        max_retries: int = 2,
        secondary_client: Optional[Union[LLMClient, BaseLLMClient]] = None,
    ) -> CompilationResult:
        """Perform dual-pass cross-extraction agreement on a regulatory clause.

        1. Pass A: Conservative literal extraction.
        2. Pass B: Structural decomposition extraction (with secondary prompt or client).
        3. Logic comparison: If passes disagree, rule is marked PENDING_REVIEW.
        4. If both passes agree and pass verification, rule is marked APPROVED.
        5. Supports CONDITIONAL_RULE outcome identification.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Empty raw_text provided to compile_clause_with_agreement.")
            return CompilationResult(
                rule=None,
                secondary_rule=None,
                cross_agreement=False,
                review_status="REJECTED",
                outcome_type="STANDARD",
                discrepancies=["Empty clause text."],
            )

        # Pass A
        rule_a, report_a = self._extract_single_pass(
            raw_text=raw_text,
            source_metadata=source_metadata,
            prompt_generator=construct_initial_prompt,
            client=self.llm_client,
            max_retries=max_retries,
        )

        # Pass B (distinct prompt; optional distinct client)
        client_b = secondary_client or self.llm_client
        rule_b, report_b = self._extract_single_pass(
            raw_text=raw_text,
            source_metadata=source_metadata,
            prompt_generator=construct_secondary_prompt,
            client=client_b,
            max_retries=max_retries,
        )

        # Outcome type detection (v4 §8.3 [G] CONDITIONAL_RULE)
        outcome_type = "STANDARD"
        for r in (rule_a, rule_b):
            if r and (
                r.verification.status in ("CONDITIONAL_RULE", "conditional_rule")
                or getattr(r, "outcome_type", "") == "CONDITIONAL_RULE"
            ):
                outcome_type = "CONDITIONAL_RULE"
                break

        # Check for non-compilable status
        if rule_a and rule_a.verification.status.upper() == "NON_COMPILABLE":
            return CompilationResult(
                rule=rule_a,
                secondary_rule=rule_b,
                cross_agreement=False,
                review_status="NON_COMPILABLE",
                outcome_type=outcome_type,
                discrepancies=["Clause designated NON_COMPILABLE by extractor."],
                verification_report=report_a,
            )

        # If Pass A failed verification
        if not rule_a:
            return CompilationResult(
                rule=None,
                secondary_rule=rule_b,
                cross_agreement=False,
                review_status="REJECTED",
                outcome_type=outcome_type,
                discrepancies=["Pass A failed verification or schema validation."],
                verification_report=report_a,
            )

        # If Pass B failed verification
        if not rule_b:
            # Rule A passed verification, but second pass failed -> PENDING_REVIEW
            rule_a.verification.agreement = False
            rule_a.verification.status = "PENDING_REVIEW"
            return CompilationResult(
                rule=rule_a,
                secondary_rule=None,
                cross_agreement=False,
                review_status="PENDING_REVIEW",
                outcome_type=outcome_type,
                discrepancies=["Pass B failed extraction/verification."],
                verification_report=report_a,
            )

        # Compare logic between Pass A and Pass B
        agreed, discrepancies = compute_rule_agreement(rule_a, rule_b)

        if agreed:
            rule_a.verification.agreement = True
            rule_a.verification.status = "APPROVED"
            review_status = "APPROVED"
        else:
            rule_a.verification.agreement = False
            rule_a.verification.status = "PENDING_REVIEW"
            review_status = "PENDING_REVIEW"
            logger.warning(
                "Cross-extraction disagreement on %s (%d discrepancies): %s",
                rule_a.rule_id,
                len(discrepancies),
                "; ".join(discrepancies),
            )

        return CompilationResult(
            rule=rule_a,
            secondary_rule=rule_b,
            cross_agreement=agreed,
            review_status=review_status,
            outcome_type=outcome_type,
            discrepancies=discrepancies,
            verification_report=report_a,
        )
