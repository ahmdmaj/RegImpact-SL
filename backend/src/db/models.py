"""SQLAlchemy 2.0 ORM models for RegImpact-SL Milestone 1.

Tables:
  source_documents    – Immutable source snapshot with SHA-256 hash guard.
  document_pages      – Raw page text with character offsets and OCR flag.
  clauses             – Segmented clauses with composite PK (clause_id, version_number).
  rules               – Persistent rules derived from clauses, with review states.
  human_review_audit  – Ordered audit log of every reviewer decision on a rule.

Design notes:
  - JSON columns use SQLAlchemy's standard JSON type which works on both
    PostgreSQL (natively) and SQLite (as TEXT with Python serialisation).
  - pgvector embedding columns are NOT included — planned for Milestone 3.
  - The ClauseORM.rules relationship uses explicit foreign_keys to handle the
    composite FK without relying on ambiguous string-based primaryjoin.
"""

import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime.datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Table: source_documents
# ---------------------------------------------------------------------------

class SourceDocumentORM(Base):
    """Immutable snapshot of an authoritative regulatory source document.

    A document is uniquely identified by its SHA-256 content hash.
    Re-ingestion of a file with the same hash is rejected as a duplicate.
    Metadata that cannot be verified at ingestion time is stored as None
    and marked unresolved rather than invented.
    """

    __tablename__ = "source_documents"

    id = Column(String(128), primary_key=True, nullable=False)
    sha256_hash = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    authority = Column(String(255), nullable=False)
    instrument_type = Column(String(100), nullable=True)
    gazette_no = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)
    publication_date = Column(Date, nullable=True)
    retrieval_timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=False, default=0)
    extraction_status = Column(String(50), nullable=False, default="PENDING")
    extraction_tool = Column(String(100), nullable=True)
    extraction_warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    pages = relationship(
        "DocumentPageORM",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPageORM.page_number",
    )
    clauses = relationship(
        "ClauseORM",
        back_populates="document",
    )

    def __repr__(self) -> str:
        return f"<SourceDocumentORM id={self.id!r} sha256={self.sha256_hash[:12]!r}...>"


# ---------------------------------------------------------------------------
# Table: document_pages
# ---------------------------------------------------------------------------

class DocumentPageORM(Base):
    """Raw extracted text of a single page within a source document.

    Stores the verbatim text output from PyMuPDF / pdfplumber.
    Character-count metadata enables fast offset verification.
    The page_hash (SHA-256 of raw_text) detects accidental text corruption.
    """

    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_page_in_document"),
    )

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    document_id = Column(
        String(128),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number = Column(Integer, nullable=False)   # 1-indexed
    raw_text = Column(Text, nullable=False, default="")
    char_count = Column(Integer, nullable=False, default=0)
    is_ocr = Column(Boolean, nullable=False, default=False)
    page_hash = Column(String(64), nullable=False)  # SHA-256 of raw_text

    # Relationship
    document = relationship("SourceDocumentORM", back_populates="pages")

    def __repr__(self) -> str:
        return (
            f"<DocumentPageORM doc={self.document_id!r} "
            f"page={self.page_number} chars={self.char_count}>"
        )


# ---------------------------------------------------------------------------
# Table: clauses
# ---------------------------------------------------------------------------

class ClauseORM(Base):
    """A segmented regulatory clause anchored to its source document and page.

    Composite primary key (clause_id, version_number) supports amendment
    versioning without destroying the provenance chain.
    """

    __tablename__ = "clauses"

    clause_id = Column(String(100), primary_key=True, nullable=False)
    version_number = Column(Integer, primary_key=True, nullable=False, default=1)
    document_id = Column(
        String(128),
        ForeignKey("source_documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clause_number = Column(String(100), nullable=False)
    text = Column(Text, nullable=False)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)
    char_start = Column(Integer, nullable=False, default=0)
    char_end = Column(Integer, nullable=False, default=0)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    transition_until = Column(Date, nullable=True)
    superseded_by_clause_id = Column(String(100), nullable=True)
    applied_patches = Column(JSON, nullable=True)
    is_compilable = Column(Boolean, nullable=False, default=True)
    non_compilable_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    document = relationship("SourceDocumentORM", back_populates="clauses")
    # rules relationship is defined on RuleORM side via back_populates

    def __repr__(self) -> str:
        return (
            f"<ClauseORM id={self.clause_id!r} v{self.version_number} "
            f"pages={self.start_page}-{self.end_page}>"
        )


# ---------------------------------------------------------------------------
# Table: rules
# ---------------------------------------------------------------------------

class RuleORM(Base):
    """A persistent regulatory rule compiled from a clause.

    review_status lifecycle:
      DRAFT           – Initial extraction / seed state.
      PENDING_REVIEW  – Awaiting human verification.
      APPROVED        – Verified; eligible for deterministic execution.
      REJECTED        – Rejected due to grounding or semantic defect.
      NON_COMPILABLE  – Clause is legally ambiguous or discretionary.

    outcome_type:
      STANDARD        – Fully profile-evaluable by the engine.
      CONDITIONAL_RULE – Has a statutory precondition the engine cannot
                         resolve from profile fields alone (v4 §8.3 [G]).
    """

    __tablename__ = "rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["clause_id", "clause_version"],
            ["clauses.clause_id", "clauses.version_number"],
        ),
    )

    rule_id = Column(String(100), primary_key=True, nullable=False)
    clause_id = Column(String(100), nullable=False, index=True)
    clause_version = Column(Integer, nullable=False)
    outcome_type = Column(String(50), nullable=False, default="STANDARD")

    # Rule logic stored as JSON (mirrors Pydantic domain model structure)
    applies_if = Column(JSON, nullable=False)
    exceptions = Column(JSON, nullable=True)
    obligation = Column(JSON, nullable=False)
    validity = Column(JSON, nullable=False)
    source = Column(JSON, nullable=False)

    # Review state
    review_status = Column(String(50), nullable=False, default="DRAFT")
    is_gold_rule = Column(Boolean, nullable=False, default=False)

    # Extraction provenance
    extraction_model = Column(String(100), nullable=True)
    extraction_prompt_hash = Column(String(64), nullable=True)
    cross_agreement = Column(Boolean, nullable=True)
    verification_report = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    audit_log = relationship(
        "HumanReviewAuditORM",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="HumanReviewAuditORM.reviewed_at",
    )

    def __repr__(self) -> str:
        return (
            f"<RuleORM id={self.rule_id!r} "
            f"status={self.review_status!r} outcome={self.outcome_type!r}>"
        )


# ---------------------------------------------------------------------------
# Table: human_review_audit
# ---------------------------------------------------------------------------

class HumanReviewAuditORM(Base):
    """Append-only audit log of every human reviewer decision on a rule.

    Reviewer roles:
      PRIMARY_ANNOTATOR    – First-pass human extraction / verification.
      SECONDARY_ANNOTATOR  – Independent cross-check annotator.
      EXPERT_ADJUDICATOR   – External domain expert resolving disagreements.

    Decisions:
      APPROVED | REJECTED | MARKED_NON_COMPILABLE | AMENDED
    """

    __tablename__ = "human_review_audit"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    rule_id = Column(
        String(100),
        ForeignKey("rules.rule_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(String(100), nullable=False)
    reviewer_role = Column(String(50), nullable=False)
    decision = Column(String(50), nullable=False)
    rationale = Column(Text, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationship
    rule = relationship("RuleORM", back_populates="audit_log")

    def __repr__(self) -> str:
        return (
            f"<HumanReviewAuditORM rule={self.rule_id!r} "
            f"decision={self.decision!r} reviewer={self.reviewer_id!r}>"
        )
