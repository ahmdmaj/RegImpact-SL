"""Repository pattern for RegImpact-SL — Milestone 1.

Provides:
  BaseRegulatoryRepository   – abstract interface consumed by the engine and API.
  InMemoryRepository         – existing in-memory implementation (preserved).
  PostgresRegulatoryRepository – SQLAlchemy-backed persistent implementation.

Bidirectional adapters between ORM models and Pydantic domain models are
kept inside this module so that domain.py and the applicability engine never
import SQLAlchemy.

Design constraints (from alignment plan §10):
  - Do NOT weaken or delete existing behaviour exposed by InMemoryRepository.
  - The API continues to default to InMemoryRepository unless DATABASE_URL is
    configured, so existing tests require zero changes.
  - Only APPROVED rules are returned for deterministic execution (enforcement
    point: get_approved_rules / get_rules_for_evaluation).
"""

from __future__ import annotations

import datetime
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.src.models.domain import (
    AppliesIf,
    ClauseVersion,
    Condition,
    Obligation,
    Rule,
    Source,
    Validity,
    Verification,
)

if TYPE_CHECKING:
    from backend.src.db.models import (
        ClauseORM,
        HumanReviewAuditORM,
        RuleORM,
        SourceDocumentORM,
    )

logger = logging.getLogger(__name__)


# ===========================================================================
# Abstract base repository interface
# ===========================================================================

class BaseRegulatoryRepository(ABC):
    """Abstract interface for regulatory data access.

    Consumers of this interface (engine, API, benchmark runner) must not
    depend on concrete storage details.
    """

    # --- Rule access --------------------------------------------------------

    @abstractmethod
    def add_rule(self, rule: Rule) -> None:
        """Persist a rule. Raises ValueError if rule_id already exists."""

    @abstractmethod
    def get_all_rules(self) -> List[Rule]:
        """Return all rules (for seeded demo/test data compatibility)."""

    @abstractmethod
    def get_approved_rules(self) -> List[Rule]:
        """Return only rules with review_status == APPROVED (for production evaluation)."""

    @abstractmethod
    def get_rules_by_ids(self, ids: List[str]) -> List[Rule]:
        """Return rules matching any of the supplied rule_id or clause values."""

    # --- Clause version access ----------------------------------------------

    @abstractmethod
    def add_clause_version(self, cv: ClauseVersion) -> None:
        """Persist a clause version."""

    @abstractmethod
    def get_clause_versions(self) -> List[ClauseVersion]:
        """Return all clause versions."""


# ===========================================================================
# In-Memory Repository (original implementation — unchanged)
# ===========================================================================

class InMemoryRepository(BaseRegulatoryRepository):
    """In-memory store for Rule and ClauseVersion objects.

    This is the original Phase A implementation.  It is preserved exactly
    so that all existing unit tests continue to pass without modification.
    """

    def __init__(self) -> None:
        self.rules: Dict[str, Rule] = {}
        self.clause_versions: Dict[str, ClauseVersion] = {}

    def add_rule(self, rule: Rule) -> None:
        self.rules[rule.rule_id] = rule
        self.rules[rule.source.clause] = rule

    def add_clause_version(self, cv: ClauseVersion) -> None:
        self.clause_versions[cv.clause_id] = cv

    def get_all_rules(self) -> List[Rule]:
        seen: Set[str] = set()
        unique_rules: List[Rule] = []
        for r in self.rules.values():
            if r.rule_id not in seen:
                seen.add(r.rule_id)
                unique_rules.append(r)
        return unique_rules

    def get_approved_rules(self) -> List[Rule]:
        """For the in-memory store all seeded rules are treated as approved."""
        return self.get_all_rules()

    def get_rules_by_ids(self, ids: List[str]) -> List[Rule]:
        result: List[Rule] = []
        seen: Set[str] = set()
        for identifier in ids:
            r = self.rules.get(identifier)
            if r and r.rule_id not in seen:
                seen.add(r.rule_id)
                result.append(r)
        return result

    def get_clause_versions(self) -> List[ClauseVersion]:
        return list(self.clause_versions.values())


# ===========================================================================
# Bidirectional adapters (ORM ↔ Pydantic domain)
# ===========================================================================

def _parse_date(value: Any) -> Optional[str]:
    """Coerce a date/datetime/string to an ISO-8601 string, or None."""
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()[:10]
    return str(value)


def rule_orm_to_domain(orm: "RuleORM") -> Rule:
    """Convert a RuleORM record into a Pydantic Rule domain model."""
    # source JSON → Source
    src_dict: Dict[str, Any] = orm.source or {}
    source = Source(
        instrument=src_dict.get("instrument", ""),
        authority=src_dict.get("authority", ""),
        gazette_no=src_dict.get("gazette_no", ""),
        clause=src_dict.get("clause", ""),
        page=int(src_dict.get("page", 0)),
        quote_span=src_dict.get("quote_span", ""),
    )

    # validity JSON → Validity
    val_dict: Dict[str, Any] = orm.validity or {}
    validity = Validity(
        published=val_dict.get("published", ""),
        commences=val_dict.get("commences", ""),
        transition_until=val_dict.get("transition_until"),
        superseded_by=val_dict.get("superseded_by"),
        superseded_date=val_dict.get("superseded_date"),
    )

    # applies_if JSON → AppliesIf
    ai_dict: Dict[str, Any] = orm.applies_if or {}
    all_conds = [
        Condition(field=c["field"], op=c["op"], value=c["value"])
        for c in (ai_dict.get("all") or [])
    ]
    any_conds = [
        Condition(field=c["field"], op=c["op"], value=c["value"])
        for c in (ai_dict.get("any") or [])
    ]
    applies_if = AppliesIf(all=all_conds or None, any=any_conds or None)

    # obligation JSON → Obligation
    obl_dict: Dict[str, Any] = orm.obligation or {}
    obligation = Obligation(
        type=obl_dict.get("type", ""),
        text=obl_dict.get("text", ""),
        impact_categories=obl_dict.get("impact_categories", []),
        disclosures=obl_dict.get("disclosures"),
    )

    # verification — stored in source JSON or verification_report JSON
    ver_dict: Dict[str, Any] = orm.verification_report or {}
    verification = Verification(
        status=ver_dict.get("status", orm.review_status),
        extraction_model=orm.extraction_model or "unknown",
        agreement=bool(orm.cross_agreement) if orm.cross_agreement is not None else True,
        reason=ver_dict.get("reason"),
        justification=ver_dict.get("justification"),
    )

    rule = Rule(
        rule_id=orm.rule_id,
        source=source,
        validity=validity,
        applies_if=applies_if,
        exceptions=list(orm.exceptions or []),
        obligation=obligation,
        verification=verification,
    )
    if hasattr(orm, "outcome_type") and orm.outcome_type:
        setattr(rule, "outcome_type", orm.outcome_type)
    return rule


def rule_domain_to_orm_dict(rule: Rule, clause_id: str, clause_version: int) -> Dict[str, Any]:
    """Serialise a Pydantic Rule into a dict suitable for constructing RuleORM."""
    applies_if_dict: Dict[str, Any] = {}
    if rule.applies_if.all:
        applies_if_dict["all"] = [
            {"field": c.field, "op": c.op, "value": c.value}
            for c in rule.applies_if.all
        ]
    if rule.applies_if.any:
        applies_if_dict["any"] = [
            {"field": c.field, "op": c.op, "value": c.value}
            for c in rule.applies_if.any
        ]

    return {
        "rule_id": rule.rule_id,
        "clause_id": clause_id,
        "clause_version": clause_version,
        "applies_if": applies_if_dict,
        "exceptions": [
            e if isinstance(e, dict) else e.model_dump()
            for e in (rule.exceptions or [])
        ],
        "obligation": {
            "type": rule.obligation.type,
            "text": rule.obligation.text,
            "impact_categories": rule.obligation.impact_categories,
            "disclosures": rule.obligation.disclosures,
        },
        "validity": {
            "published": rule.validity.published,
            "commences": rule.validity.commences,
            "transition_until": rule.validity.transition_until,
            "superseded_by": rule.validity.superseded_by,
            "superseded_date": getattr(rule.validity, "superseded_date", None),
        },
        "source": {
            "instrument": rule.source.instrument,
            "authority": rule.source.authority,
            "gazette_no": rule.source.gazette_no,
            "clause": rule.source.clause,
            "page": rule.source.page,
            "quote_span": rule.source.quote_span,
        },
        "review_status": rule.verification.status if rule.verification.status else "DRAFT",
        "outcome_type": getattr(rule, "outcome_type", None) or (
            "CONDITIONAL_RULE" if (rule.verification.status or "").upper() == "CONDITIONAL_RULE" else "STANDARD"
        ),
        "extraction_model": rule.verification.extraction_model,
        "verification_report": {
            "status": rule.verification.status,
            "reason": rule.verification.reason,
            "justification": rule.verification.justification,
        },
        "cross_agreement": rule.verification.agreement,
    }


def clause_orm_to_domain(orm: "ClauseORM") -> ClauseVersion:
    """Convert a ClauseORM record into a Pydantic ClauseVersion domain model."""
    return ClauseVersion(
        clause_id=orm.clause_id,
        instrument=orm.document.title if orm.document else "",
        version_number=orm.version_number,
        text=orm.text,
        valid_from=_parse_date(orm.valid_from) or "",
        valid_to=_parse_date(orm.valid_to),
        applied_patches=list(orm.applied_patches or []),
    )


# ===========================================================================
# PostgreSQL / SQLAlchemy-backed Repository
# ===========================================================================

class PostgresRegulatoryRepository(BaseRegulatoryRepository):
    """Persistent repository backed by PostgreSQL (or SQLite in tests).

    All mutations are committed immediately to the injected Session.
    The caller is responsible for transaction management (the session_scope
    context manager in session.py handles this for non-FastAPI callers).

    Constraint: only APPROVED rules are returned by get_approved_rules().
    get_all_rules() returns every rule (for inspection / seeding purposes).
    """

    # Sentinel clause version used when persisting a Rule that came from
    # InMemoryRepository seed data (where we have no real ClauseORM record).
    _SEED_CLAUSE_VERSION = 1

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_seed_clause(self, rule: Rule) -> tuple[str, int]:
        """Ensure a minimal ClauseORM exists for a seeded/demo rule.

        Seed rules (manual-gold or demo fixtures) do not go through the full
        ingestion pipeline, so we create a lightweight placeholder clause record
        attached to a placeholder document if necessary.

        Returns (clause_id, version_number).
        """
        from backend.src.db.models import ClauseORM, SourceDocumentORM

        # Derive a deterministic clause_id from the rule's source clause field
        clause_id = rule.source.clause.upper().replace(" ", "-")[:100]
        clause_version = self._SEED_CLAUSE_VERSION

        existing = (
            self._session.query(ClauseORM)
            .filter_by(clause_id=clause_id, version_number=clause_version)
            .first()
        )
        if existing:
            return clause_id, clause_version

        # Check if seed document exists
        doc_id = "doc_seed_demo_fixtures"
        doc = self._session.get(SourceDocumentORM, doc_id)
        if doc is None:
            doc = SourceDocumentORM(
                id=doc_id,
                sha256_hash="0" * 64,
                title="Demo / Seed Fixtures (NOT authoritative corpus)",
                authority="INTERNAL",
                file_path="backend/data/seed_fixtures",
                file_size_bytes=0,
                page_count=0,
                extraction_status="SEED",
                extraction_tool="manual",
            )
            self._session.add(doc)
            self._session.flush()

        clause = ClauseORM(
            clause_id=clause_id,
            version_number=clause_version,
            document_id=doc_id,
            clause_number=rule.source.clause,
            text=rule.source.quote_span,
            start_page=rule.source.page,
            end_page=rule.source.page,
            char_start=0,
            char_end=len(rule.source.quote_span),
            valid_from=None,
            is_compilable=True,
        )
        self._session.add(clause)
        self._session.flush()
        return clause_id, clause_version

    # ------------------------------------------------------------------
    # Rule operations
    # ------------------------------------------------------------------

    def add_rule(self, rule: Rule) -> None:
        from backend.src.db.models import RuleORM

        if self._session.get(RuleORM, rule.rule_id) is not None:
            logger.warning("Rule %r already exists in the database — skipping.", rule.rule_id)
            return

        clause_id, clause_version = self._get_or_create_seed_clause(rule)
        data = rule_domain_to_orm_dict(rule, clause_id, clause_version)
        orm = RuleORM(**data)
        self._session.add(orm)
        self._session.flush()
        logger.debug("Persisted rule %r (clause %r v%s).", rule.rule_id, clause_id, clause_version)

    def get_all_rules(self) -> List[Rule]:
        from backend.src.db.models import RuleORM

        rows = self._session.query(RuleORM).all()
        rules: List[Rule] = []
        for row in rows:
            try:
                rules.append(rule_orm_to_domain(row))
            except Exception as exc:
                logger.error("Failed to deserialise rule %r: %s", row.rule_id, exc)
        return rules

    def get_approved_rules(self) -> List[Rule]:
        from backend.src.db.models import RuleORM

        rows = (
            self._session.query(RuleORM)
            .filter(RuleORM.review_status == "APPROVED")
            .all()
        )
        rules: List[Rule] = []
        for row in rows:
            try:
                rules.append(rule_orm_to_domain(row))
            except Exception as exc:
                logger.error("Failed to deserialise rule %r: %s", row.rule_id, exc)
        return rules

    def get_rules_by_ids(self, ids: List[str]) -> List[Rule]:
        from backend.src.db.models import RuleORM

        seen: Set[str] = set()
        result: List[Rule] = []
        for identifier in ids:
            row = self._session.get(RuleORM, identifier)
            if row and row.rule_id not in seen:
                seen.add(row.rule_id)
                try:
                    result.append(rule_orm_to_domain(row))
                except Exception as exc:
                    logger.error("Failed to deserialise rule %r: %s", row.rule_id, exc)
        return result

    # ------------------------------------------------------------------
    # Clause version operations
    # ------------------------------------------------------------------

    def add_clause_version(self, cv: ClauseVersion) -> None:
        from backend.src.db.models import ClauseORM

        clause_id = cv.clause_id
        version = cv.version_number
        existing = (
            self._session.query(ClauseORM)
            .filter_by(clause_id=clause_id, version_number=version)
            .first()
        )
        if existing:
            logger.warning(
                "ClauseVersion (%r, v%s) already exists — skipping.", clause_id, version
            )
            return

        doc_id = "doc_seed_demo_fixtures"
        from backend.src.db.models import SourceDocumentORM
        doc = self._session.get(SourceDocumentORM, doc_id)
        if doc is None:
            doc = SourceDocumentORM(
                id=doc_id,
                sha256_hash="0" * 64,
                title="Demo / Seed Fixtures (NOT authoritative corpus)",
                authority="INTERNAL",
                file_path="backend/data/seed_fixtures",
                file_size_bytes=0,
                page_count=0,
                extraction_status="SEED",
                extraction_tool="manual",
            )
            self._session.add(doc)
            self._session.flush()

        valid_from_date: Optional[datetime.date] = None
        if cv.valid_from:
            try:
                valid_from_date = datetime.date.fromisoformat(str(cv.valid_from)[:10])
            except ValueError:
                pass

        clause = ClauseORM(
            clause_id=clause_id,
            version_number=version,
            document_id=doc_id,
            clause_number=clause_id,
            text=cv.text,
            start_page=1,
            end_page=1,
            char_start=0,
            char_end=len(cv.text),
            valid_from=valid_from_date,
            is_compilable=True,
        )
        self._session.add(clause)
        self._session.flush()

    def get_clause_versions(self) -> List[ClauseVersion]:
        from backend.src.db.models import ClauseORM

        rows = (
            self._session.query(ClauseORM)
            .order_by(ClauseORM.clause_id, ClauseORM.version_number)
            .all()
        )
        result: List[ClauseVersion] = []
        for row in rows:
            try:
                result.append(clause_orm_to_domain(row))
            except Exception as exc:
                logger.error(
                    "Failed to deserialise clause (%r, v%s): %s",
                    row.clause_id, row.version_number, exc
                )
        return result
