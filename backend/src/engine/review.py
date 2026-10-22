"""Component [F]: Human review state machine and audit service for RegImpact-SL.

Implements the human review workflow for compiled regulatory rules:
  1. Validates reviewer identity and roles (PRIMARY_ANNOTATOR, SECONDARY_ANNOTATOR, EXPERT_ADJUDICATOR).
  2. Enforces valid decision transitions (APPROVED, REJECTED, MARKED_NON_COMPILABLE, AMENDED).
  3. Updates rule status and designates gold rules when adjudicated by experts.
  4. Records immutable audit trail entries in human_review_audit table.
  5. Provides pending review queue and audit trail lookup.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from backend.src.db.models import HumanReviewAuditORM, RuleORM

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

ROLE_PRIMARY_ANNOTATOR = "PRIMARY_ANNOTATOR"
ROLE_SECONDARY_ANNOTATOR = "SECONDARY_ANNOTATOR"
ROLE_EXPERT_ADJUDICATOR = "EXPERT_ADJUDICATOR"

VALID_REVIEWER_ROLES: Set[str] = {
    ROLE_PRIMARY_ANNOTATOR,
    ROLE_SECONDARY_ANNOTATOR,
    ROLE_EXPERT_ADJUDICATOR,
}

DECISION_APPROVED = "APPROVED"
DECISION_REJECTED = "REJECTED"
DECISION_MARKED_NON_COMPILABLE = "MARKED_NON_COMPILABLE"
DECISION_AMENDED = "AMENDED"

VALID_DECISIONS: Set[str] = {
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_MARKED_NON_COMPILABLE,
    DECISION_AMENDED,
}


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class ReviewError(Exception):
    """Base exception for review workflow errors."""
    pass


class RuleNotFoundError(ReviewError):
    """Raised when a rule is not found in the database."""
    pass


class InvalidReviewerRoleError(ReviewError):
    """Raised when an unrecognised or unauthorized reviewer role is provided."""
    pass


class InvalidReviewDecisionError(ReviewError):
    """Raised when an invalid review decision is submitted."""
    pass


# ---------------------------------------------------------------------------
# Review Service
# ---------------------------------------------------------------------------

class ReviewService:
    """Service governing human review transitions and audit logging for regulatory rules."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def submit_review(
        self,
        rule_id: str,
        reviewer_id: str,
        reviewer_role: str,
        decision: str,
        rationale: str,
        amendments: Optional[Dict[str, Any]] = None,
    ) -> RuleORM:
        """Submit a human reviewer decision on a rule and record an audit log.

        Args:
            rule_id: Primary key of the rule in rules table.
            reviewer_id: Stable identifier of the human reviewer (e.g. 'annotator_01').
            reviewer_role: Role of the reviewer (PRIMARY_ANNOTATOR | SECONDARY_ANNOTATOR | EXPERT_ADJUDICATOR).
            decision: Decision (APPROVED | REJECTED | MARKED_NON_COMPILABLE | AMENDED).
            rationale: Mandatory substantive explanation justifying the decision.
            amendments: Optional dictionary of amended fields (applies_if, obligation, validity, exceptions).

        Returns:
            The updated RuleORM entity.

        Raises:
            RuleNotFoundError: If rule_id does not exist in database.
            InvalidReviewerRoleError: If reviewer_role is invalid.
            InvalidReviewDecisionError: If decision is invalid.
            ValueError: If rationale or reviewer_id is blank.
        """
        if not reviewer_id or not reviewer_id.strip():
            raise ValueError("reviewer_id must be a non-empty string.")

        role_clean = (reviewer_role or "").strip().upper()
        if role_clean not in VALID_REVIEWER_ROLES:
            raise InvalidReviewerRoleError(
                f"Invalid reviewer_role: {reviewer_role!r}. "
                f"Must be one of {sorted(VALID_REVIEWER_ROLES)}"
            )

        decision_clean = (decision or "").strip().upper()
        if decision_clean not in VALID_DECISIONS:
            raise InvalidReviewDecisionError(
                f"Invalid review decision: {decision!r}. "
                f"Must be one of {sorted(VALID_DECISIONS)}"
            )

        if not rationale or not rationale.strip():
            raise ValueError("rationale must be provided and cannot be empty.")

        rule = self.db.get(RuleORM, rule_id)
        if rule is None:
            raise RuleNotFoundError(f"Rule with id {rule_id!r} not found in database.")

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # Apply state transition
        if decision_clean == DECISION_APPROVED:
            rule.review_status = "APPROVED"
            if role_clean == ROLE_EXPERT_ADJUDICATOR:
                rule.is_gold_rule = True

        elif decision_clean == DECISION_REJECTED:
            rule.review_status = "REJECTED"
            rule.is_gold_rule = False

        elif decision_clean == DECISION_MARKED_NON_COMPILABLE:
            rule.review_status = "NON_COMPILABLE"
            rule.is_gold_rule = False

        elif decision_clean == DECISION_AMENDED:
            rule.review_status = "APPROVED"
            # Version preservation: capture immutable snapshot of prior rule state before mutation
            prior_state = {
                "applies_if": rule.applies_if,
                "obligation": rule.obligation,
                "validity": rule.validity,
                "exceptions": rule.exceptions,
                "outcome_type": rule.outcome_type,
                "review_status": rule.review_status,
            }
            rep = dict(rule.verification_report) if isinstance(rule.verification_report, dict) else {}
            history = list(rep.get("version_history", []))
            history.append({
                "amended_at": now_utc.isoformat(),
                "amended_by": reviewer_id.strip(),
                "reviewer_role": role_clean,
                "prior_state": prior_state,
                "rationale": rationale.strip(),
            })
            rep["version_history"] = history
            rule.verification_report = rep

            if amendments:
                if "applies_if" in amendments:
                    rule.applies_if = amendments["applies_if"]
                if "obligation" in amendments:
                    rule.obligation = amendments["obligation"]
                if "validity" in amendments:
                    rule.validity = amendments["validity"]
                if "exceptions" in amendments:
                    rule.exceptions = amendments["exceptions"]
                if "outcome_type" in amendments:
                    rule.outcome_type = amendments["outcome_type"]
            if role_clean == ROLE_EXPERT_ADJUDICATOR:
                rule.is_gold_rule = True

        rule.updated_at = now_utc

        # Insert immutable audit entry
        audit_record = HumanReviewAuditORM(
            rule_id=rule_id,
            reviewer_id=reviewer_id.strip(),
            reviewer_role=role_clean,
            decision=decision_clean,
            rationale=rationale.strip(),
            reviewed_at=now_utc,
        )
        self.db.add(audit_record)
        self.db.commit()
        self.db.refresh(rule)

        logger.info(
            "Review submitted for rule %s: %s by %s (%s). New status: %s",
            rule_id,
            decision_clean,
            reviewer_id,
            role_clean,
            rule.review_status,
        )
        return rule

    def get_pending_reviews(self) -> List[RuleORM]:
        """Fetch all rules awaiting review (status is PENDING_REVIEW or DRAFT)."""
        return (
            self.db.query(RuleORM)
            .filter(RuleORM.review_status.in_(["PENDING_REVIEW", "DRAFT"]))
            .order_by(RuleORM.created_at.asc())
            .all()
        )

    def get_approved_rules(self) -> List[RuleORM]:
        """Fetch all rules eligible for deterministic engine evaluation."""
        return (
            self.db.query(RuleORM)
            .filter(RuleORM.review_status == "APPROVED")
            .order_by(RuleORM.created_at.asc())
            .all()
        )

    def get_gold_rules(self) -> List[RuleORM]:
        """Fetch all human expert adjudicated gold standard rules."""
        return (
            self.db.query(RuleORM)
            .filter(RuleORM.is_gold_rule == True)  # noqa: E712
            .order_by(RuleORM.created_at.asc())
            .all()
        )

    def get_audit_trail(self, rule_id: str) -> List[HumanReviewAuditORM]:
        """Retrieve the complete chronological audit trail for a rule."""
        rule = self.db.get(RuleORM, rule_id)
        if rule is None:
            raise RuleNotFoundError(f"Rule with id {rule_id!r} not found.")

        return (
            self.db.query(HumanReviewAuditORM)
            .filter_by(rule_id=rule_id)
            .order_by(HumanReviewAuditORM.reviewed_at.asc())
            .all()
        )
