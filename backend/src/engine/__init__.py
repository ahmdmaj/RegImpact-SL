"""Deterministic applicability, impact, and verification engine package."""
from backend.src.engine.applicability import (
    evaluate_rule,
    evaluate_condition,
    evaluate_temporal_validity,
    extract_field,
    generate_counterfactuals,
)
from backend.src.engine.impact_mapper import (
    map_impact,
    BusinessImpact,
    SUPPORTED_OBLIGATION_TYPES,
)
from backend.src.engine.verifier import (
    RuleVerifier,
    verify_rule,
    VerificationReport,
    VerificationIssue,
)

from backend.src.engine.versioning import (
    PatchError,
    PatchOperation,
    PatchType,
    ClauseVersion,
    apply_patch,
    apply_patches,
    create_clause_version,
)

from backend.src.engine.evidence import (
    EvidenceChecker,
    EvidenceCheckResult,
    EvidenceError,
)

__all__ = [
    "evaluate_rule",
    "evaluate_condition",
    "evaluate_temporal_validity",
    "extract_field",
    "generate_counterfactuals",
    "map_impact",
    "BusinessImpact",
    "SUPPORTED_OBLIGATION_TYPES",
    "RuleVerifier",
    "verify_rule",
    "VerificationReport",
    "VerificationIssue",
    "PatchError",
    "PatchOperation",
    "PatchType",
    "ClauseVersion",
    "apply_patch",
    "apply_patches",
    "create_clause_version",
    "EvidenceChecker",
    "EvidenceCheckResult",
    "EvidenceError",
]




