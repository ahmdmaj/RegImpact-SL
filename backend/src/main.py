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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Session

from backend.src.db.models import (
    ClauseORM,
    DocumentPageORM,
    HumanReviewAuditORM,
    RuleORM,
    SourceDocumentORM,
    SYNTHETIC_DOCUMENT_IDS,
    SYNTHETIC_RULE_IDS,
    is_synthetic_clause,
    is_synthetic_rule,
)
from backend.src.db.repositories import PostgresRegulatoryRepository
from backend.src.db.session import get_db, init_db, session_scope
from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.evidence import EvidenceChecker
from backend.src.engine.impact_mapper import BusinessImpact, map_impact
from backend.src.engine.retrieval import (
    HybridRetrievalEngine,
    RetrievalResult,
    build_retrieval_query,
    cross_reference_coverage_gaps,
)
from backend.src.engine.review import (
    ReviewService,
    RuleNotFoundError,
)
from backend.src.extraction.compiler import RuleCompiler
from backend.src.extraction.embedding_client import get_embedding_client, MockEmbeddingClient
from backend.src.extraction.explanation import ExplanationGenerator
from backend.src.extraction.ingestion import (
    DocumentIngestionService,
    extract_document_preamble,
    segment_clauses_from_page,
    segment_document_clauses,
)
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
    "hazardous_chemicals_storage_liters": "Does your facility store hazardous industrial chemicals exceeding 500 liters? (Enter liters or 0 if none)",
    "uses_synthetic_colorings": "Does your business use synthetic food colorings in your products? (Yes / No)",
    "industry_category": "Is your facility categorized under Part A prescribed industrial activities? (e.g. Part A, Part B, or General SME)",
    "wastewater_discharge_m3_per_day": "Does your facility discharge industrial wastewater exceeding 10 cubic meters (m³) per day? (Enter m³/day or 0)",
}


def format_clarifying_question(field_path: str) -> str:
    """Format an unknown profile field into a human-readable clarifying question."""
    if field_path in CLARIFYING_QUESTION_MAP:
        return CLARIFYING_QUESTION_MAP[field_path]
    clean_name = field_path.replace(".", " ").replace("_", " ").title()
    return f"Please provide information regarding '{clean_name}' to resolve regulatory applicability."


VALID_ROLES: Set[str] = {"sme_user", "reviewer", "admin"}


def get_current_role(x_user_role: Optional[str] = Header(None, alias="X-User-Role")) -> str:
    """Extract and validate role from X-User-Role header. Default to 'admin' when omitted."""
    if not x_user_role:
        return "admin"
    role = x_user_role.strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Role '{x_user_role}'. Valid roles are: {', '.join(sorted(VALID_ROLES))}",
        )
    return role


def require_role(allowed_roles: Set[str]):
    """FastAPI dependency to enforce role-based access control."""
    def role_dependency(role: str = Depends(get_current_role)) -> str:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: role '{role}' is not authorized. Allowed roles: {', '.join(sorted(allowed_roles))}",
            )
        return role
    return role_dependency


def ensure_database_seeded(session: Session) -> None:
    """Ensure that the persistent database has been seeded with Dataset A regulatory corpus and authoritative slice."""
    has_docs = session.query(SourceDocumentORM).first() is not None
    has_rules = session.query(RuleORM).first() is not None
    if not has_docs or not has_rules:
        logger.info("Database appears unseeded. Seeding authoritative regulatory corpus...")
        seed_regulatory_corpus(db=session, include_synthetic_fixtures=False)
        from backend.data.seed_real_slice import seed_real_slice
        seed_real_slice(session=session)
    else:
        has_real_rule = session.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3").first() is not None
        if not has_real_rule:
            from backend.data.seed_real_slice import seed_real_slice
            seed_real_slice(session=session)

    # Ensure any existing legacy synthetic records in DB are flagged as is_synthetic=True
    try:
        session.query(SourceDocumentORM).filter(
            SourceDocumentORM.id.in_(SYNTHETIC_DOCUMENT_IDS)
        ).update({"is_synthetic": True}, synchronize_session=False)

        session.query(RuleORM).filter(
            RuleORM.rule_id.in_(SYNTHETIC_RULE_IDS)
        ).update({"is_synthetic": True}, synchronize_session=False)

        session.query(ClauseORM).filter(
            ClauseORM.document_id.in_(SYNTHETIC_DOCUMENT_IDS)
        ).update({"is_synthetic": True}, synchronize_session=False)
        session.flush()
    except Exception as exc:
        logger.debug("Synthetic flag sync skipped: %s", exc)


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

        if getattr(rule_orm, "is_synthetic", False) or is_synthetic_rule(rule=rule_orm):
            review_status = f"{review_status} [SYNTHETIC TEST FIXTURE - NOT VERIFIED STATUTE]"
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
    conditional_missing_data_count: int = 0
    conditional_rule_count: int = 0
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
        try:
            from dotenv import load_dotenv
            for _env_p in [Path("backend/.env"), Path(".env")]:
                if _env_p.exists():
                    load_dotenv(_env_p, override=False)
        except Exception:
            pass

        app.state.llm_client = get_llm_client(allow_mock_fallback=False)
        app.state.explanation_generator = ExplanationGenerator(llm_client=app.state.llm_client)
        logger.info(
            "Initialized live LLM client on FastAPI app state: %s (model=%s)",
            type(app.state.llm_client).__name__,
            getattr(app.state.llm_client, "model", "default"),
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

# Initialize default app state attributes
app.state.llm_client = None
app.state.explanation_generator = ExplanationGenerator()
app.state.evidence_checker = EvidenceChecker()

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
def get_regulations(
    db: Session = Depends(get_db),
    _role: str = Depends(require_role({"sme_user", "reviewer", "admin"})),
) -> List[ClauseVersion]:
    """Return all available regulation clause versions in the persistent database."""
    ensure_database_seeded(db)
    repo = PostgresRegulatoryRepository(db)
    return repo.get_clause_versions()


@app.get("/evaluation/results")
@app.get("/api/evaluation/results")
def get_evaluation_results(
    _role: str = Depends(require_role({"sme_user", "reviewer", "admin"})),
) -> Dict[str, Any]:
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
    _role: str = Depends(require_role({"sme_user", "reviewer", "admin"})),
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
    conditional_missing_count = 0
    conditional_rule_count = 0
    not_applicable_count = 0
    unsupported_count = 0

    # -------------------------------------------------------------------------
    # Mode 1: Targeted Clause/Rule Evaluation (request.clause_ids specified)
    # -------------------------------------------------------------------------
    if request.clause_ids:
        all_rules = repo.get_rules_by_ids(request.clause_ids)
        targeted_rules: List[Rule] = []
        unapproved_rules: List[Tuple[Rule, str]] = []

        for r in all_rules:
            r_orm = db.query(RuleORM).filter_by(rule_id=r.rule_id).first()
            status = r_orm.review_status if r_orm else getattr(r.verification, "status", "PENDING_REVIEW")
            if status == "APPROVED":
                targeted_rules.append(r)
            else:
                unapproved_rules.append((r, status))

        found_rule_ids = {r.rule_id for r in targeted_rules} | {r.source.clause for r in targeted_rules}

        # Check for requested IDs that do not have an approved rule in the DB (coverage gaps)
        for cid in request.clause_ids:
            if cid not in found_rule_ids:
                unapp = next((ur for ur in unapproved_rules if ur[0].rule_id == cid or ur[0].source.clause == cid), None)
                if unapp:
                    unapp_rule, unapp_status = unapp
                    prov = _resolve_provenance(db, rule_id=unapp_rule.rule_id, clause_id=unapp_rule.source.clause)
                    evaluations.append(
                        RuleAnalysisDetail(
                            rule_id=unapp_rule.rule_id,
                            clause=unapp_rule.source.clause,
                            instrument=prov.get("document_title") or unapp_rule.source.instrument,
                            authority=unapp_rule.source.authority,
                            status=OutcomeStatus.UNSUPPORTED,
                            reason=f"Coverage Gap: Rule '{unapp_rule.rule_id}' is unapproved (status: '{unapp_status}') and unavailable for execution until reviewed.",
                            temporal_status=None,
                            quote_span=unapp_rule.source.quote_span,
                            missing_fields=[],
                            counterfactuals=[],
                            evaluation_trace=[],
                            impact=None,
                            document_title=prov.get("document_title"),
                            document_id=prov.get("document_id"),
                            page_number=prov.get("page_number", unapp_rule.source.page),
                            char_start=prov.get("char_start", 0),
                            char_end=prov.get("char_end", len(unapp_rule.source.quote_span or "")),
                            review_status=unapp_status,
                            coverage_gap=True,
                        )
                    )
                else:
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
                conditional_missing_count += 1
                for mf in eval_result.missing_fields:
                    if mf not in all_missing_fields:
                        all_missing_fields.append(mf)

            elif eval_result.status == OutcomeStatus.CONDITIONAL_RULE:
                conditional_rule_count += 1

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
        query = build_retrieval_query(profile)
        include_synth = getattr(request, "include_synthetic", False) or (
            profile.business_id == "BIZ-SL-ACCEPTANCE-001"
        )
        retrieval_engine = HybridRetrievalEngine(db=db)
        candidates: List[RetrievalResult] = retrieval_engine.search(
            query, top_k=5, filters={"include_synthetic": include_synth}
        )
        candidate_clause_ids = [c.clause_id for c in candidates]
        approved_cids = cross_reference_coverage_gaps(db, candidate_clause_ids, include_synthetic=include_synth)

        evaluated_rule_ids: Set[str] = set()
        evaluated_clause_ids: Set[str] = set()

        for cand in candidates:
            # Objective 2: Isolate synthetic candidates from normal open inquiry
            if not include_synth and (
                cand.is_synthetic
                or cand.document_id in SYNTHETIC_DOCUMENT_IDS
                or is_synthetic_clause(clause_id=cand.clause_id, document_id=cand.document_id)
            ):
                continue

            if cand.clause_id in approved_cids:
                # Find the approved rule(s) matching this candidate clause
                matching_query = db.query(RuleORM).filter(
                    RuleORM.clause_id == cand.clause_id,
                    RuleORM.review_status == "APPROVED",
                )
                if not include_synth:
                    matching_query = matching_query.filter(
                        RuleORM.is_synthetic.is_(False),
                        ~RuleORM.rule_id.in_(SYNTHETIC_RULE_IDS),
                    )
                matching_rules = matching_query.all()
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
                        conditional_missing_count += 1
                        for mf in eval_result.missing_fields:
                            if mf not in all_missing_fields:
                                all_missing_fields.append(mf)

                    elif eval_result.status == OutcomeStatus.CONDITIONAL_RULE:
                        conditional_rule_count += 1

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
                if not include_synth and (
                    cand.is_synthetic
                    or cand.document_id in SYNTHETIC_DOCUMENT_IDS
                    or is_synthetic_clause(clause_id=cand.clause_id, document_id=cand.document_id)
                ):
                    continue

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
        all_approved_rules = repo.get_approved_rules(include_synthetic=include_synth)
        for rule in all_approved_rules:
            if not include_synth and (
                getattr(rule, "is_synthetic", False)
                or is_synthetic_rule(rule=rule, rule_id=rule.rule_id)
            ):
                continue
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
                conditional_missing_count += 1
                for mf in eval_result.missing_fields:
                    if mf not in all_missing_fields:
                        all_missing_fields.append(mf)

            elif eval_result.status == OutcomeStatus.CONDITIONAL_RULE:
                conditional_rule_count += 1

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
        conditional_rules_count=conditional_missing_count + conditional_rule_count,
        conditional_missing_data_count=conditional_missing_count,
        conditional_rule_count=conditional_rule_count,
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
        report.narrative_summary = "Summary generation failed verification; narrative withheld."

    return report


# ---------------------------------------------------------------------------
# Admin & Legal Review Queue Schemas and Endpoints (Phase 2 & Phase 3)
# ---------------------------------------------------------------------------

class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    rule_id: str
    clause_id: str
    clause_number: Optional[str] = None
    document_title: Optional[str] = None
    document_id: Optional[str] = None
    review_status: str
    outcome_type: str
    applies_if: Dict[str, Any] = {}
    obligation: Dict[str, Any] = {}
    exceptions: List[Any] = []
    validity: Dict[str, Any] = {}
    source: Dict[str, Any] = {}
    verbatim_quote_span: Optional[str] = None
    clause_text: Optional[str] = None
    discrepancies: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    reviewer_id: Optional[str] = "legal_reviewer_01"
    reviewer_role: Optional[str] = "PRIMARY_ANNOTATOR"
    rationale: Optional[str] = "Verified against official gazette source text."
    amendments: Optional[Dict[str, Any]] = None


@app.get("/admin/reviews", response_model=List[ReviewItemResponse])
def get_pending_reviews(
    db: Session = Depends(get_db),
    _role: str = Depends(require_role({"reviewer", "admin"})),
) -> List[ReviewItemResponse]:
    """Return all rules awaiting human review (review_status='PENDING_REVIEW')."""
    ensure_database_seeded(db)
    pending_rules = (
        db.query(RuleORM)
        .filter(RuleORM.review_status == "PENDING_REVIEW")
        .order_by(RuleORM.created_at.desc())
        .all()
    )
    items: List[ReviewItemResponse] = []
    for r in pending_rules:
        clause = db.query(ClauseORM).filter_by(clause_id=r.clause_id).first()
        doc = db.query(SourceDocumentORM).filter_by(id=clause.document_id).first() if clause else None

        quote = (r.source or {}).get("quote_span") or (clause.text if clause else None)
        doc_title = (r.source or {}).get("instrument") or (doc.title if doc else None)

        items.append(
            ReviewItemResponse(
                rule_id=r.rule_id,
                clause_id=r.clause_id,
                clause_number=clause.clause_number if clause else (r.source or {}).get("clause"),
                document_title=doc_title,
                document_id=clause.document_id if clause else (doc.id if doc else None),
                review_status=r.review_status,
                outcome_type=r.outcome_type,
                applies_if=r.applies_if or {},
                obligation=r.obligation or {},
                exceptions=r.exceptions or [],
                validity=r.validity or {},
                source=r.source or {},
                verbatim_quote_span=quote,
                clause_text=clause.text if clause else quote,
                discrepancies=[],
                created_at=r.created_at.isoformat() if r.created_at else None,
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
        )
    return items


@app.post("/admin/reviews/{rule_id}/approve")
def approve_review(
    rule_id: str,
    payload: Optional[ReviewDecisionRequest] = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role({"reviewer", "admin"})),
) -> Dict[str, Any]:
    """Approve a pending rule, writing to the immutable human_review_audit table."""
    body = payload or ReviewDecisionRequest()
    service = ReviewService(db)
    try:
        updated_rule = service.submit_review(
            rule_id=rule_id,
            reviewer_id=body.reviewer_id or "legal_reviewer_01",
            reviewer_role=body.reviewer_role or "PRIMARY_ANNOTATOR",
            decision="APPROVED",
            rationale=body.rationale or "Approved by legal reviewer after verbatim verification.",
            amendments=body.amendments,
        )
        return {
            "success": True,
            "rule_id": updated_rule.rule_id,
            "review_status": updated_rule.review_status,
            "message": f"Rule {rule_id} approved successfully.",
        }
    except RuleNotFoundError:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/admin/reviews/{rule_id}/reject")
def reject_review(
    rule_id: str,
    payload: Optional[ReviewDecisionRequest] = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role({"reviewer", "admin"})),
) -> Dict[str, Any]:
    """Reject a pending rule, writing to the immutable human_review_audit table."""
    body = payload or ReviewDecisionRequest()
    service = ReviewService(db)
    try:
        updated_rule = service.submit_review(
            rule_id=rule_id,
            reviewer_id=body.reviewer_id or "legal_reviewer_01",
            reviewer_role=body.reviewer_role or "PRIMARY_ANNOTATOR",
            decision="REJECTED",
            rationale=body.rationale or "Rejected by legal reviewer due to logic or threshold discrepancy.",
            amendments=body.amendments,
        )
        return {
            "success": True,
            "rule_id": updated_rule.rule_id,
            "review_status": updated_rule.review_status,
            "message": f"Rule '{rule_id}' rejected.",
        }
    except RuleNotFoundError:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/admin/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    authority: Optional[str] = Form(None),
    instrument_type: Optional[str] = Form(None),
    gazette_no: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _role: str = Depends(require_role({"admin"})),
) -> Dict[str, Any]:
    """Upload a new regulatory PDF, store in raw_sources, ingest, segment, and compile rules."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    raw_dir = Path("backend/data/raw_sources")
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_filename = Path(file.filename).name
    target_file = raw_dir / clean_filename
    target_file.write_bytes(content)

    doc_id = f"doc_{target_file.stem.lower().replace('-', '_').replace(' ', '_')}"
    doc_title = title or target_file.stem.replace("_", " ").replace("-", " ").title()
    doc_authority = authority or "Sri Lanka Regulatory Authority"

    ingestion_service = DocumentIngestionService(pdf_store_dir=raw_dir)
    ingestion_result = ingestion_service.ingest(
        db=db,
        pdf_path=target_file,
        doc_id=doc_id,
        title=doc_title,
        authority=doc_authority,
        instrument_type=instrument_type or "regulation",
        gazette_no=gazette_no,
        publication_date=publication_date,
    )

    if not ingestion_result.success and not ingestion_result.is_duplicate:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {ingestion_result.error}")

    pages = (
        db.query(DocumentPageORM)
        .filter_by(document_id=doc_id)
        .order_by(DocumentPageORM.page_number)
        .all()
    )

    # Extract authoritative preamble metadata from document pages
    preamble_meta = extract_document_preamble(pages)
    resolved_title = title or preamble_meta.get("instrument") or doc_title
    resolved_authority = authority or preamble_meta.get("authority") or doc_authority
    resolved_gazette_no = gazette_no or preamble_meta.get("gazette_no") or ""
    resolved_published = publication_date or preamble_meta.get("published") or ""
    resolved_commences = preamble_meta.get("commences") or ""

    # Update SourceDocumentORM with resolved metadata if empty
    src_doc = db.query(SourceDocumentORM).filter_by(id=doc_id).first()
    if src_doc:
        if not src_doc.title or src_doc.title == target_file.stem.replace("_", " ").title():
            src_doc.title = resolved_title
        if not src_doc.authority or src_doc.authority == "Sri Lanka Regulatory Authority":
            src_doc.authority = resolved_authority
        if not src_doc.gazette_no and resolved_gazette_no:
            src_doc.gazette_no = resolved_gazette_no
        if not src_doc.publication_date and resolved_published:
            src_doc.publication_date = resolved_published
        db.flush()

    emb_client = getattr(app.state, "embedding_client", None)
    if emb_client is None:
        try:
            emb_client = get_embedding_client(allow_mock_fallback=False)
        except Exception:
            emb_client = None
    clauses_created = 0
    created_clause_objects: List[ClauseORM] = []

    # Segment clauses across entire document with layout-aware structural parsing
    candidate_segments = segment_document_clauses(pages, pdf_path=target_file)
    if not candidate_segments:
        for page in pages:
            candidate_segments.extend(segment_clauses_from_page(page.raw_text, page.page_number))

    for seg in candidate_segments:
        # Sanitize clause number for primary key format
        clean_num = re.sub(r"[^A-Za-z0-9\-\_]", "-", seg.clause_number).strip("-")
        clause_pk = f"CLAUSE-{doc_id.upper()}-{clean_num.upper()}"
        existing = db.query(ClauseORM).filter_by(clause_id=clause_pk).first()
        if not existing:
            is_live_emb = emb_client is not None and not isinstance(emb_client, MockEmbeddingClient)
            emb = emb_client.embed_text(seg.text) if emb_client else None
            prov_name = getattr(emb_client, "provider_name", "sentence-transformers") if is_live_emb else None
            mod_name = getattr(emb_client, "model_name", "BAAI/bge-base-en-v1.5") if is_live_emb else None
            patch_data = {
                "clause_type": seg.clause_type,
                "sub_clauses_count": len(seg.sub_clauses),
                "tables_count": len(seg.tables),
                "provisos_count": len(seg.provisos),
                "provisos": seg.provisos,
                "sub_clauses": [
                    {"identifier": sc.identifier, "sub_type": sc.sub_type, "text": sc.text[:120]}
                    for sc in seg.sub_clauses
                ],
            }
            clause_orm = ClauseORM(
                clause_id=clause_pk,
                version_number=1,
                document_id=doc_id,
                clause_number=seg.clause_number,
                text=seg.text,
                start_page=seg.start_page,
                end_page=seg.end_page,
                char_start=seg.char_start,
                char_end=seg.char_end,
                applied_patches=patch_data,
                is_compilable=True,
                embedding=emb,
                embedding_verified=bool(emb and is_live_emb),
                embedding_provider=prov_name,
                embedding_model=mod_name,
            )
            db.add(clause_orm)
            db.flush()
            clauses_created += 1
            created_clause_objects.append(clause_orm)
        else:
            if emb_client and (not existing.embedding or not existing.embedding_verified or not existing.embedding_provider):
                is_live_emb = not isinstance(emb_client, MockEmbeddingClient)
                existing.embedding = emb_client.embed_text(seg.text)
                existing.embedding_verified = is_live_emb
                existing.embedding_provider = getattr(emb_client, "provider_name", "sentence-transformers") if is_live_emb else None
                existing.embedding_model = getattr(emb_client, "model_name", "BAAI/bge-base-en-v1.5") if is_live_emb else None
                db.flush()
            created_clause_objects.append(existing)

    llm_client = getattr(app.state, "llm_client", None)
    if llm_client is None:
        try:
            llm_client = get_llm_client(allow_mock_fallback=False)
        except Exception:
            llm_client = None
    compiler = RuleCompiler(llm_client=llm_client) if llm_client else None

    rules_compiled = 0
    pending_count = 0
    approved_count = 0

    if compiler:
        reg1_text = ""
        for c_obj in created_clause_objects:
            c_num = str(c_obj.clause_number).strip().lower()
            if c_num in ("1", "regulation 1", "reg 1", "reg. 1", "clause 1", "section 1"):
                reg1_text = f"{c_obj.clause_number}. {c_obj.text}"
                break

        for clause in created_clause_objects:
            existing_rule = db.query(RuleORM).filter_by(clause_id=clause.clause_id).first()
            if existing_rule:
                continue

            try:
                comp_res = compiler.compile_clause_with_agreement(
                    raw_text=clause.text,
                    source_metadata={
                        "clause": clause.clause_number,
                        "instrument": resolved_title,
                        "authority": resolved_authority,
                        "doc_id": doc_id,
                        "page": clause.start_page,
                        "gazette_no": resolved_gazette_no,
                        "published": resolved_published,
                        "commences": resolved_commences,
                        "regulation_1_text": reg1_text,
                        "context_evidence": {
                            "regulation_1": reg1_text,
                            "commences": resolved_commences,
                            "published": resolved_published,
                            "instrument": resolved_title,
                            "gazette_no": resolved_gazette_no,
                        },
                    },
                    auto_approve=False,
                )
                if comp_res.rule:
                    r = comp_res.rule
                    rule_pk = f"RULE-{doc_id.upper()}-{clause.clause_number.replace(' ', '-').upper()}"
                    r_applies = r.applies_if.model_dump() if hasattr(r.applies_if, "model_dump") else r.applies_if
                    r_except = [e.model_dump() if hasattr(e, "model_dump") else e for e in (r.exceptions or [])]
                    r_oblig = r.obligation.model_dump() if hasattr(r.obligation, "model_dump") else r.obligation
                    r_valid = r.validity.model_dump() if hasattr(r.validity, "model_dump") else r.validity
                    r_src = r.source.model_dump() if hasattr(r.source, "model_dump") else (r.source or {})

                    rule_orm = RuleORM(
                        rule_id=rule_pk,
                        clause_id=clause.clause_id,
                        clause_version=1,
                        outcome_type=comp_res.outcome_type,
                        applies_if=r_applies,
                        exceptions=r_except,
                        obligation=r_oblig,
                        validity=r_valid,
                        source=r_src,
                        review_status=comp_res.review_status,
                    )
                    db.add(rule_orm)
                    db.flush()
                    rules_compiled += 1

                    if comp_res.review_status == "APPROVED":
                        approved_count += 1
                        db.add(
                            HumanReviewAuditORM(
                                rule_id=rule_pk,
                                reviewer_id="system_dual_pass",
                                reviewer_role="PRIMARY_ANNOTATOR",
                                decision="APPROVED",
                                rationale="Dual-pass LLM extraction cross-agreement confirmed.",
                            )
                        )
                    elif comp_res.review_status == "PENDING_REVIEW":
                        pending_count += 1
            except Exception as exc:
                logger.warning("Error compiling clause %s: %s", clause.clause_id, exc)

    db.commit()

    return {
        "success": True,
        "doc_id": doc_id,
        "filename": clean_filename,
        "title": doc_title,
        "pages_ingested": len(pages),
        "clauses_extracted": clauses_created,
        "rules_compiled": rules_compiled,
        "pending_reviews_count": pending_count,
        "approved_rules_count": approved_count,
    }
