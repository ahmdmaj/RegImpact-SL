"""FastAPI Application for RegImpact-SL — Milestone 7.

Exposes REST APIs for:
- Health checks (GET /health)
- Regulatory catalog and clause versions (GET /regulations)
- Regulatory change impact analysis (POST /analysis) with persistent DB + hybrid retrieval
- Benchmark evaluation results (GET /evaluation/results, GET /api/evaluation/results)
"""

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, HumanReviewAuditORM, RuleORM, SourceDocumentORM
from backend.src.db.repositories import PostgresRegulatoryRepository
from backend.src.db.session import get_db, init_db, session_scope
from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.evidence import EvidenceChecker
from backend.src.engine.impact_mapper import BusinessImpact, map_impact
from backend.src.engine.retrieval import (
    HybridRetrievalEngine,
    RetrievalResult,
    cross_reference_coverage_gaps,
)
from backend.src.extraction.explanation import ExplanationGenerator
from backend.src.extraction.llm_client import get_llm_client
from backend.src.models.domain import (
    BusinessProfile,
    ClauseVersion,
    OutcomeStatus,
    Rule,
)
from backend.src.scripts.seed_corpus import seed_regulatory_corpus

logger = logging.getLogger(__name__)

# Friendly mapping from missing profile field paths to SME clarifying questions
CLARIFYING_QUESTION_MAP: Dict[str, str] = {
    "production_capacity.kg_per_day": "What is your facility's daily production capacity in kilograms (kg/day)?",
    "production_capacity.value": "What is your total installed production capacity volume?",
    "products.prepackaged": "Does your business manufacture or package prepackaged food products for retail sale?",
    "activity": "What primary industrial activity or food processing does your business conduct?",
    "employee_count": "How many total employees (full-time and part-time) work in your manufacturing enterprise?",
    "market.domestic": "Do you sell your products in the Sri Lankan domestic market?",
    "market.export_flag": "Does your business export any manufactured food products overseas?",
    "market.import_flag": "Does your business import raw materials or finished products from overseas?",
    "premises.type": "What is the physical classification of your premises (e.g. factory, cottage industry, commercial kitchen)?",
    "premises.location_authority_area": "In which Local Authority area (Municipal Council / Urban Council / Pradeshiya Sabha) are your premises located?",
}


def format_clarifying_question(field_path: str) -> str:
    """Format an unknown profile field into a human-readable clarifying question."""
    if field_path in CLARIFYING_QUESTION_MAP:
        return CLARIFYING_QUESTION_MAP[field_path]
    clean_name = field_path.replace(".", " ").replace("_", " ").title()
    return f"Please provide information regarding '{clean_name}' to resolve regulatory applicability."


def ensure_database_seeded(session: Session) -> None:
    """Ensure that the persistent database has been seeded with Dataset A regulatory corpus."""
    has_docs = session.query(SourceDocumentORM).first() is not None
    has_rules = session.query(RuleORM).first() is not None
    if not has_docs or not has_rules:
        logger.info("Database appears unseeded. Seeding authoritative regulatory corpus...")
        seed_regulatory_corpus(db=session)


def _resolve_provenance(db: Session, rule_id: str, clause_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve strict persistent provenance and audit trail for a rule or clause."""
    rule_orm = db.query(RuleORM).filter_by(rule_id=rule_id).first()
    if not rule_orm and clause_id:
        rule_orm = db.query(RuleORM).filter_by(clause_id=clause_id).first()

    clause_orm = None
    if rule_orm:
        clause_orm = db.query(ClauseORM).filter_by(clause_id=rule_orm.clause_id).first()
    elif clause_id:
        clause_orm = db.query(ClauseORM).filter_by(clause_id=clause_id).first()

    doc_orm = None
    if clause_orm and clause_orm.document:
        doc_orm = clause_orm.document
    elif clause_orm:
        doc_orm = db.query(SourceDocumentORM).filter_by(id=clause_orm.document_id).first()

    review_status = "APPROVED"
    if rule_orm:
        if rule_orm.audit_log:
            latest_audit = sorted(rule_orm.audit_log, key=lambda a: str(a.reviewed_at), reverse=True)[0]
            review_status = f"{rule_orm.review_status} by {latest_audit.reviewer_role}"
        else:
            review_status = rule_orm.review_status
    elif clause_orm:
        review_status = "UNVERIFIED_SOURCE_CLAUSE"

    return {
        "document_title": doc_orm.title if doc_orm else (clause_orm.document_id if clause_orm else None),
        "document_id": clause_orm.document_id if clause_orm else (doc_orm.id if doc_orm else None),
        "page_number": clause_orm.start_page if clause_orm else 1,
        "char_start": clause_orm.char_start if clause_orm else 0,
        "char_end": clause_orm.char_end if clause_orm else (len(clause_orm.text) if clause_orm else 0),
        "review_status": review_status,
    }


# Request and Response Schemas
class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    business_profile: Optional[BusinessProfile] = None
    profile: Optional[BusinessProfile] = None
    as_at_date: Optional[str] = None
    clause_ids: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def extract_profile(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "business_profile" not in data and "profile" not in data:
                profile_fields = {
                    "business_id",
                    "industry",
                    "activity",
                    "employee_count",
                    "products",
                    "production_capacity",
                    "premises",
                    "market",
                    "existing_licences",
                }
                if any(k in data for k in profile_fields):
                    prof_data = {k: v for k, v in data.items() if k not in ("as_at_date", "clause_ids")}
                    data["business_profile"] = prof_data
        return data


class RuleAnalysisDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    rule_id: str
    clause: str
    instrument: str
    authority: str
    status: OutcomeStatus
    reason: Optional[str] = None
    temporal_status: Optional[str] = None
    quote_span: Optional[str] = None
    missing_fields: List[str] = []
    counterfactuals: List[str] = []
    evaluation_trace: List[Dict[str, Any]] = []
    impact: Optional[BusinessImpact] = None

    # Milestone 7 Persistent Provenance & Audit Trail metadata
    document_title: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    review_status: Optional[str] = None
    coverage_gap: bool = False


class StructuredImpactReport(BaseModel):
    model_config = ConfigDict(extra="allow")
    as_at_date: str
    total_rules_evaluated: int
    applicable_rules_count: int
    conditional_rules_count: int
    not_applicable_rules_count: int
    unsupported_rules_count: int
    missing_fields: List[str] = []
    clarifying_questions: List[str] = []
    action_checklist: List[str] = []
    affected_activities: List[str] = []
    affected_documents: List[str] = []
    narrative_summary: Optional[str] = None
    evaluations: List[RuleAnalysisDetail] = []


# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise persistent database and ensure regulatory corpus is seeded
    init_db()
    with session_scope() as session:
        ensure_database_seeded(session)

    # Initialize live LLM client on application startup
    try:
        app.state.llm_client = get_llm_client(allow_mock_fallback=True)
        app.state.explanation_generator = ExplanationGenerator(llm_client=app.state.llm_client)
        logger.info(
            "Initialized live LLM client on FastAPI app state: %s",
            type(app.state.llm_client).__name__,
        )
    except Exception as exc:
        logger.warning(
            "Could not initialize live LLM client (%s); using deterministic explanation generator.",
            exc,
        )
        app.state.llm_client = None
        app.state.explanation_generator = ExplanationGenerator()

    yield


# FastAPI Application Setup
app = FastAPI(
    title="RegImpact-SL API",
    description="Deterministic regulatory impact analysis pipeline for Sri Lankan small food manufacturers.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development (Section 8.7 thin UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/regulations", response_model=List[ClauseVersion])
def get_regulations(db: Session = Depends(get_db)) -> List[ClauseVersion]:
    """Return all available regulation clause versions in the persistent database."""
    ensure_database_seeded(db)
    repo = PostgresRegulatoryRepository(db)
    return repo.get_clause_versions()


@app.get("/evaluation/results")
@app.get("/api/evaluation/results")
def get_evaluation_results() -> Dict[str, Any]:
    """Return the latest compiled benchmark evaluation results and clustered statistical testing."""
    primary_path = Path("backend/data/evaluation/results.json")
    if not primary_path.exists():
        primary_path = Path(__file__).resolve().parent.parent.parent / "data" / "evaluation" / "results.json"
    if not primary_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation results not yet compiled.")
    with open(primary_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.post("/analysis", response_model=StructuredImpactReport)
def run_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> StructuredImpactReport:
    """Execute regulatory impact analysis with persistent DB, retrieval, and coverage gap detection."""
    ensure_database_seeded(db)
    repo = PostgresRegulatoryRepository(db)

    # Resolve business profile
    profile = request.business_profile or request.profile
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="Request must contain a valid business profile (under 'business_profile', 'profile', or root level).",
        )

    # Resolve evaluation date
    eval_date = request.as_at_date or profile.as_at_date or "2024-08-01"

    evaluations: List[RuleAnalysisDetail] = []
    all_missing_fields: List[str] = []
    all_actions: List[str] = []
    all_activities: List[str] = []
    all_documents: List[str] = []

    applicable_count = 0
    conditional_count = 0
    not_applicable_count = 0
    unsupported_count = 0

    # -------------------------------------------------------------------------
    # Mode 1: Targeted Clause/Rule Evaluation (request.clause_ids specified)
    # -------------------------------------------------------------------------
    if request.clause_ids:
        targeted_rules = repo.get_rules_by_ids(request.clause_ids)
        found_rule_ids = {r.rule_id for r in targeted_rules} | {r.source.clause for r in targeted_rules}

        # Check for requested IDs that do not have an approved rule in the DB (coverage gaps)
        for cid in request.clause_ids:
            if cid not in found_rule_ids:
                prov = _resolve_provenance(db, rule_id=cid, clause_id=cid)
                evaluations.append(
                    RuleAnalysisDetail(
                        rule_id=cid,
                        clause=cid,
                        instrument=prov.get("document_title") or "Regulatory Corpus",
                        authority="Statutory Authority",
                        status=OutcomeStatus.UNSUPPORTED,
                        reason=f"Coverage Gap: Target clause/rule '{cid}' lacks an approved executable rule.",
                        temporal_status=None,
                        quote_span=None,
                        missing_fields=[],
                        counterfactuals=[],
                        evaluation_trace=[],
                        impact=None,
                        document_title=prov.get("document_title"),
                        document_id=prov.get("document_id"),
                        page_number=prov.get("page_number", 1),
                        char_start=prov.get("char_start", 0),
                        char_end=prov.get("char_end", 0),
                        review_status="UNSUPPORTED_COVERAGE_GAP",
                        coverage_gap=True,
                    )
                )
                unsupported_count += 1

        # Evaluate found approved rules
        for rule in targeted_rules:
            eval_result = evaluate_rule(rule=rule, profile=profile, as_at_date=eval_date)
            prov = _resolve_provenance(db, rule_id=rule.rule_id, clause_id=rule.source.clause)

            impact_detail: Optional[BusinessImpact] = None
            if eval_result.status == OutcomeStatus.APPLICABLE:
                applicable_count += 1
                impact_detail = map_impact(rule, eval_result)
                if impact_detail:
                    for act in impact_detail.action_items:
                        if act not in all_actions:
                            all_actions.append(act)
                    for a in impact_detail.affected_activities:
                        if a not in all_activities:
                            all_activities.append(a)
                    for d in impact_detail.affected_documents:
                        if d not in all_documents:
                            all_documents.append(d)

            elif eval_result.status == OutcomeStatus.CONDITIONAL_MISSING_DATA:
                conditional_count += 1
                for mf in eval_result.missing_fields:
                    if mf not in all_missing_fields:
                        all_missing_fields.append(mf)

            elif eval_result.status == OutcomeStatus.NOT_APPLICABLE:
                not_applicable_count += 1

            elif eval_result.status == OutcomeStatus.UNSUPPORTED:
                unsupported_count += 1

            evaluations.append(
                RuleAnalysisDetail(
                    rule_id=rule.rule_id,
                    clause=rule.source.clause,
                    instrument=rule.source.instrument,
                    authority=rule.source.authority,
                    status=eval_result.status,
                    reason=eval_result.reason,
                    temporal_status=eval_result.temporal_status,
                    quote_span=rule.source.quote_span,
                    missing_fields=eval_result.missing_fields,
                    counterfactuals=eval_result.counterfactuals,
                    evaluation_trace=eval_result.evaluation_trace,
                    impact=impact_detail,
                    document_title=prov.get("document_title") or rule.source.instrument,
                    document_id=prov.get("document_id"),
                    page_number=prov.get("page_number", rule.source.page),
                    char_start=prov.get("char_start", 0),
                    char_end=prov.get("char_end", len(rule.source.quote_span or "")),
                    review_status=prov.get("review_status", "APPROVED"),
                    coverage_gap=False,
                )
            )

    # -------------------------------------------------------------------------
    # Mode 2: Open-Inquiry Pipeline (System P: Retrieval + Coverage Gaps)
    # -------------------------------------------------------------------------
    else:
        query = f"{profile.activity or ''} {profile.industry or ''}".strip() or "food manufacturing"
        retrieval_engine = HybridRetrievalEngine(db=db)
        candidates: List[RetrievalResult] = retrieval_engine.search(query, top_k=5)
        candidate_clause_ids = [c.clause_id for c in candidates]
        approved_cids = cross_reference_coverage_gaps(db, candidate_clause_ids)

        evaluated_rule_ids: Set[str] = set()
        evaluated_clause_ids: Set[str] = set()

        for cand in candidates:
            if cand.clause_id in approved_cids:
                # Find the approved rule(s) matching this candidate clause
                matching_rules = (
                    db.query(RuleORM)
                    .filter(
                        RuleORM.clause_id == cand.clause_id,
                        RuleORM.review_status == "APPROVED",
                    )
                    .all()
                )
                from backend.src.db.repositories import rule_orm_to_domain
                for r_orm in matching_rules:
                    rule = rule_orm_to_domain(r_orm)
                    if rule.rule_id in evaluated_rule_ids:
                        continue
                    evaluated_rule_ids.add(rule.rule_id)
                    evaluated_clause_ids.add(cand.clause_id)

                    eval_result = evaluate_rule(rule=rule, profile=profile, as_at_date=eval_date)
                    prov = _resolve_provenance(db, rule_id=rule.rule_id, clause_id=cand.clause_id)

                    impact_detail: Optional[BusinessImpact] = None
                    if eval_result.status == OutcomeStatus.APPLICABLE:
                        applicable_count += 1
                        impact_detail = map_impact(rule, eval_result)
                        if impact_detail:
                            for act in impact_detail.action_items:
                                if act not in all_actions:
                                    all_actions.append(act)
                            for a in impact_detail.affected_activities:
                                if a not in all_activities:
                                    all_activities.append(a)
                            for d in impact_detail.affected_documents:
                                if d not in all_documents:
                                    all_documents.append(d)

                    elif eval_result.status == OutcomeStatus.CONDITIONAL_MISSING_DATA:
                        conditional_count += 1
                        for mf in eval_result.missing_fields:
                            if mf not in all_missing_fields:
                                all_missing_fields.append(mf)

                    elif eval_result.status == OutcomeStatus.NOT_APPLICABLE:
                        not_applicable_count += 1

                    elif eval_result.status == OutcomeStatus.UNSUPPORTED:
                        unsupported_count += 1

                    evaluations.append(
                        RuleAnalysisDetail(
                            rule_id=rule.rule_id,
                            clause=rule.source.clause,
                            instrument=rule.source.instrument,
                            authority=rule.source.authority,
                            status=eval_result.status,
                            reason=eval_result.reason,
                            temporal_status=eval_result.temporal_status,
                            quote_span=rule.source.quote_span,
                            missing_fields=eval_result.missing_fields,
                            counterfactuals=eval_result.counterfactuals,
                            evaluation_trace=eval_result.evaluation_trace,
                            impact=impact_detail,
                            document_title=prov.get("document_title") or cand.document_title or rule.source.instrument,
                            document_id=prov.get("document_id") or cand.document_id,
                            page_number=prov.get("page_number", rule.source.page),
                            char_start=prov.get("char_start", 0),
                            char_end=prov.get("char_end", len(rule.source.quote_span or "")),
                            review_status=prov.get("review_status", "APPROVED"),
                            coverage_gap=False,
                        )
                    )
            else:
                # Candidate clause was retrieved but lacks an approved executable rule -> COVERAGE GAP
                if cand.clause_id in evaluated_clause_ids:
                    continue
                evaluated_clause_ids.add(cand.clause_id)
                prov = _resolve_provenance(db, rule_id=cand.clause_id, clause_id=cand.clause_id)
                unsupported_count += 1

                evaluations.append(
                    RuleAnalysisDetail(
                        rule_id=cand.clause_id,
                        clause=cand.clause_number,
                        instrument=cand.document_title or prov.get("document_title") or cand.document_id or "Statutory Gazette",
                        authority="Statutory Authority",
                        status=OutcomeStatus.UNSUPPORTED,
                        reason=(
                            f"Coverage Gap (System P): Candidate clause '{cand.clause_id}' ({cand.clause_number}) "
                            "was retrieved by hybrid search but does not yet have an approved executable rule."
                        ),
                        temporal_status=None,
                        quote_span=cand.text,
                        missing_fields=[],
                        counterfactuals=[],
                        evaluation_trace=[],
                        impact=None,
                        document_title=cand.document_title or prov.get("document_title"),
                        document_id=cand.document_id or prov.get("document_id"),
                        page_number=prov.get("page_number", 1),
                        char_start=prov.get("char_start", 0),
                        char_end=prov.get("char_end", len(cand.text)),
                        review_status="UNVERIFIED_SOURCE_CLAUSE",
                        coverage_gap=True,
                    )
                )

        # In addition, ensure all approved rules in the database are evaluated so the enterprise compliance
        # assessment is comprehensive across all active regulatory domains
        all_approved_rules = repo.get_approved_rules()
        for rule in all_approved_rules:
            if rule.rule_id in evaluated_rule_ids:
                continue
            evaluated_rule_ids.add(rule.rule_id)

            eval_result = evaluate_rule(rule=rule, profile=profile, as_at_date=eval_date)
            prov = _resolve_provenance(db, rule_id=rule.rule_id, clause_id=rule.source.clause)

            impact_detail: Optional[BusinessImpact] = None
            if eval_result.status == OutcomeStatus.APPLICABLE:
                applicable_count += 1
                impact_detail = map_impact(rule, eval_result)
                if impact_detail:
                    for act in impact_detail.action_items:
                        if act not in all_actions:
                            all_actions.append(act)
                    for a in impact_detail.affected_activities:
                        if a not in all_activities:
                            all_activities.append(a)
                    for d in impact_detail.affected_documents:
                        if d not in all_documents:
                            all_documents.append(d)

            elif eval_result.status == OutcomeStatus.CONDITIONAL_MISSING_DATA:
                conditional_count += 1
                for mf in eval_result.missing_fields:
                    if mf not in all_missing_fields:
                        all_missing_fields.append(mf)

            elif eval_result.status == OutcomeStatus.NOT_APPLICABLE:
                not_applicable_count += 1

            elif eval_result.status == OutcomeStatus.UNSUPPORTED:
                unsupported_count += 1

            evaluations.append(
                RuleAnalysisDetail(
                    rule_id=rule.rule_id,
                    clause=rule.source.clause,
                    instrument=rule.source.instrument,
                    authority=rule.source.authority,
                    status=eval_result.status,
                    reason=eval_result.reason,
                    temporal_status=eval_result.temporal_status,
                    quote_span=rule.source.quote_span,
                    missing_fields=eval_result.missing_fields,
                    counterfactuals=eval_result.counterfactuals,
                    evaluation_trace=eval_result.evaluation_trace,
                    impact=impact_detail,
                    document_title=prov.get("document_title") or rule.source.instrument,
                    document_id=prov.get("document_id"),
                    page_number=prov.get("page_number", rule.source.page),
                    char_start=prov.get("char_start", 0),
                    char_end=prov.get("char_end", len(rule.source.quote_span or "")),
                    review_status=prov.get("review_status", "APPROVED"),
                    coverage_gap=False,
                )
            )

    # Generate clarifying questions from all missing fields
    clarifying_questions = [
        format_clarifying_question(mf) for mf in all_missing_fields
    ]

    report = StructuredImpactReport(
        as_at_date=eval_date,
        total_rules_evaluated=len(evaluations),
        applicable_rules_count=applicable_count,
        conditional_rules_count=conditional_count,
        not_applicable_rules_count=not_applicable_count,
        unsupported_rules_count=unsupported_count,
        missing_fields=all_missing_fields,
        clarifying_questions=clarifying_questions,
        action_checklist=all_actions,
        affected_activities=all_activities,
        affected_documents=all_documents,
        evaluations=evaluations,
    )

    # Component [I] Explanation Layer & Component [J] Evidence Check
    explanation_gen = getattr(app.state, "explanation_generator", None) or ExplanationGenerator()
    summary = explanation_gen.generate_summary(report)
    evidence_checker = getattr(app.state, "evidence_checker", None) or EvidenceChecker()

    if evidence_checker.verify_claims(summary, report):
        report.narrative_summary = summary
    else:
        # If live LLM summary failed verification, fall back to deterministic grounded generator
        fallback = explanation_gen._generate_fallback_summary(report)
        if evidence_checker.verify_claims(fallback, report):
            report.narrative_summary = fallback
        else:
            report.narrative_summary = "Summary generation failed verification; narrative withheld."

    return report
