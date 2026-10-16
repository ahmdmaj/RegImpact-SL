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

from backend.src.engine.review import (
    DECISION_AMENDED,
    DECISION_APPROVED,
    DECISION_MARKED_NON_COMPILABLE,
    DECISION_REJECTED,
    InvalidReviewDecisionError,
    InvalidReviewerRoleError,
    ROLE_EXPERT_ADJUDICATOR,
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_SECONDARY_ANNOTATOR,
    ReviewError,
    ReviewService,
    RuleNotFoundError,
)

from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    BaseRetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    RetrievalResult,
    cross_reference_coverage_gaps,
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
    "ReviewService",
    "ReviewError",
    "RuleNotFoundError",
    "InvalidReviewerRoleError",
    "InvalidReviewDecisionError",
    "DECISION_APPROVED",
    "DECISION_REJECTED",
    "DECISION_MARKED_NON_COMPILABLE",
    "DECISION_AMENDED",
    "ROLE_PRIMARY_ANNOTATOR",
    "ROLE_SECONDARY_ANNOTATOR",
    "ROLE_EXPERT_ADJUDICATOR",
    "RetrievalResult",
    "BaseRetrievalEngine",
    "BM25RetrievalEngine",
    "DenseRetrievalEngine",
    "HybridRetrievalEngine",
    "cross_reference_coverage_gaps",
]




