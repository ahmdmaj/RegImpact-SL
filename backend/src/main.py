"""FastAPI Application for RegImpact-SL.

Exposes REST APIs for:
- Health checks (GET /health)
- Regulatory catalog and clause versions (GET /regulations)
- Regulatory change impact analysis (POST /analysis)
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, model_validator

from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.impact_mapper import BusinessImpact, map_impact
from backend.src.models.domain import (
    AppliesIf,
    BusinessProfile,
    ClauseVersion,
    Condition,
    Obligation,
    OutcomeStatus,
    Rule,
    Source,
    Validity,
    Verification,
)

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


# In-Memory Repository for Rules and Clause Versions
class InMemoryRepository:
    """In-memory mock store for Rule and ClauseVersion objects."""

    def __init__(self):
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


# In-Memory Seed Data
def seed_repository(repo: InMemoryRepository) -> None:
    """Populate repository with authoritative Sri Lankan food regulatory rules and clause versions."""
    # 1. FCAU Food Labelling Regulation 4
    quote_fcau = (
        "Regulation 4. Every food manufacturing enterprise having a production capacity of 50 kg per day "
        "or more, and engaged in the production of prepackaged food products, shall ensure that each retail package "
        "carries a nutrition information panel in Sinhala, Tamil, and English."
    )
    fcau_rule = Rule(
        rule_id="RULE-FCAU-001",
        source=Source(
            instrument="Food (Labelling and Advertising) Regulations",
            authority="Food Control Administration Unit (FCAU)",
            gazette_no="2024/01",
            clause="Regulation 4",
            page=1,
            quote_span=quote_fcau,
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
            transition_until="2024-12-31",
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="products.prepackaged", op="eq", value=True),
                Condition(field="production_capacity.kg_per_day", op="gte", value=50),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="labelling",
            text="Ensure retail packages carry nutritional panel in Sinhala, Tamil, and English.",
            impact_categories=["packaging", "labelling"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="manual-gold",
            agreement=True,
        ),
    )
    repo.add_rule(fcau_rule)

    fcau_clause_v1 = ClauseVersion(
        clause_id="FCAU-REG-04",
        instrument="Food (Labelling and Advertising) Regulations",
        version_number=1,
        text=quote_fcau,
        valid_from="2024-01-01",
        valid_to=None,
        applied_patches=[],
    )
    repo.add_clause_version(fcau_clause_v1)

    # 2. CEA Environmental Protection Licence (EPL) - Prescribed Activity Schedule
    quote_cea = (
        "Schedule 1 Part B Item 12. Any industrial food manufacturing activity employing 20 or more persons "
        "shall obtain an Environmental Protection Licence (EPL Category B) prior to commencing continuous operations."
    )
    cea_rule = Rule(
        rule_id="RULE-CEA-EPL-001",
        source=Source(
            instrument="National Environmental (Protection and Quality) Regulations",
            authority="Central Environmental Authority (CEA)",
            gazette_no="1533/16",
            clause="Schedule 1 Part B Item 12",
            page=3,
            quote_span=quote_cea,
        ),
        validity=Validity(
            published="2008-01-25",
            commences="2008-02-01",
            transition_until=None,
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="employee_count", op="gte", value=20),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="licensing",
            text="Obtain and renew Environmental Protection Licence (Category B) with effluent standards compliance.",
            impact_categories=["licensing", "process"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="manual-gold",
            agreement=True,
        ),
    )
    repo.add_rule(cea_rule)

    cea_clause_v1 = ClauseVersion(
        clause_id="CEA-SCHED-01-B12",
        instrument="National Environmental (Protection and Quality) Regulations",
        version_number=1,
        text=quote_cea,
        valid_from="2008-02-01",
        valid_to=None,
        applied_patches=[],
    )
    repo.add_clause_version(cea_clause_v1)


# Global in-memory repository instance
repository = InMemoryRepository()
seed_repository(repository)


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
            # If neither business_profile nor profile is explicitly passed,
            # inspect if BusinessProfile keys exist at top-level
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
    # Ensure repository is seeded
    if not repository.get_all_rules():
        seed_repository(repository)
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
def get_regulations() -> List[ClauseVersion]:
    """Return all available regulation clause versions in the system."""
    return repository.get_clause_versions()


@app.post("/analysis", response_model=StructuredImpactReport)
def run_analysis(request: AnalysisRequest) -> StructuredImpactReport:
    """Execute regulatory impact analysis over a business profile."""
    # Resolve business profile
    profile = request.business_profile or request.profile
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="Request must contain a valid business profile (under 'business_profile', 'profile', or root level).",
        )

    # Resolve evaluation date
    eval_date = request.as_at_date or profile.as_at_date or "2024-08-01"

    # Select candidate rules
    if request.clause_ids:
        candidate_rules = repository.get_rules_by_ids(request.clause_ids)
    else:
        candidate_rules = repository.get_all_rules()

    if not candidate_rules:
        return StructuredImpactReport(
            as_at_date=eval_date,
            total_rules_evaluated=0,
            applicable_rules_count=0,
            conditional_rules_count=0,
            not_applicable_rules_count=0,
            unsupported_rules_count=0,
            missing_fields=[],
            clarifying_questions=[],
            action_checklist=[],
            affected_activities=[],
            affected_documents=[],
            evaluations=[],
        )

    evaluations: List[RuleAnalysisDetail] = []
    all_missing_fields: List[str] = []
    all_actions: List[str] = []
    all_activities: List[str] = []
    all_documents: List[str] = []

    applicable_count = 0
    conditional_count = 0
    not_applicable_count = 0
    unsupported_count = 0

    for rule in candidate_rules:
        eval_result = evaluate_rule(rule=rule, profile=profile, as_at_date=eval_date)

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
                missing_fields=eval_result.missing_fields,
                counterfactuals=eval_result.counterfactuals,
                evaluation_trace=eval_result.evaluation_trace,
                impact=impact_detail,
            )
        )

    # Generate clarifying questions from all missing fields
    clarifying_questions = [
        format_clarifying_question(mf) for mf in all_missing_fields
    ]

    return StructuredImpactReport(
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
