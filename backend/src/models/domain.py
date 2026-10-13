from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, model_validator

class OutcomeStatus(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONDITIONAL_MISSING_DATA = "CONDITIONAL_MISSING_DATA"
    CONDITIONAL_RULE = "CONDITIONAL_RULE"
    UNSUPPORTED = "UNSUPPORTED"


class TriState(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class Product(BaseModel):
    model_config = ConfigDict(extra="allow")
    category: Optional[str] = None
    prepackaged: Optional[bool] = None

class ProductionCapacity(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: Optional[float] = None
    unit: Optional[str] = None
    per_period: Optional[str] = None

class Premises(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Optional[str] = None
    location_authority_area: Optional[str] = None

class Market(BaseModel):
    model_config = ConfigDict(extra="allow")
    domestic: Optional[bool] = None
    import_flag: Optional[bool] = None
    export_flag: Optional[bool] = None

class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    business_id: Optional[str] = None
    industry: Optional[str] = None
    activity: Optional[str] = None
    employee_count: Optional[int] = None
    products: Optional[List[Product]] = None
    production_capacity: Optional[ProductionCapacity] = None
    premises: Optional[Premises] = None
    market: Optional[Market] = None
    existing_licences: Optional[List[str]] = None
    as_at_date: Optional[str] = None


class Source(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument: str
    authority: str
    gazette_no: str
    clause: str
    page: int
    quote_span: str

class Validity(BaseModel):
    model_config = ConfigDict(extra="allow")
    published: str
    commences: str
    transition_until: Optional[str] = None
    superseded_by: Optional[str] = None
    superseded_date: Optional[str] = None

class Condition(BaseModel):
    model_config = ConfigDict(extra="allow")
    field: str
    op: str
    value: Any

class AppliesIf(BaseModel):
    model_config = ConfigDict(extra="allow")
    all: Optional[List[Condition]] = None
    any: Optional[List[Condition]] = None

class Obligation(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    text: str
    impact_categories: List[str]

class Verification(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str
    extraction_model: str
    agreement: bool
    reason: Optional[str] = None
    justification: Optional[str] = None

class Rule(BaseModel):
    model_config = ConfigDict(extra="allow")
    rule_id: str
    source: Source
    validity: Validity
    applies_if: AppliesIf
    exceptions: Optional[List[Any]] = []
    obligation: Obligation
    verification: Verification


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: OutcomeStatus
    rule_id: str
    missing_fields: List[str] = []
    evaluation_trace: List[Dict[str, Any]] = []
    temporal_status: Optional[str] = None
    reason: Optional[str] = None
    counterfactuals: List[str] = []


class BusinessImpact(BaseModel):
    model_config = ConfigDict(extra="allow")
    obligation_type: str
    affected_activities: List[str]
    affected_documents: List[str]
    action_items: List[str]
    timeline_note: Optional[str] = None


class VerificationIssue(BaseModel):
    model_config = ConfigDict(extra="allow")
    stage: str  # "schema", "quote_grounding", "literal_check", "consistency"
    severity: str  # "error", "warning"
    message: str


class VerificationReport(BaseModel):
    model_config = ConfigDict(extra="allow")
    is_valid: bool
    issues: List[VerificationIssue] = []
    status: str  # "verified", "rejected", "non_compilable"


class PatchType(str, Enum):
    SUBSTITUTE = "substitute"
    INSERT = "insert"
    OMIT = "omit"
    REPEAL = "repeal"


class PatchOperation(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    patch_type: PatchType
    target_text: Optional[str] = None
    replacement_text: Optional[str] = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "patch_type" not in data:
                if "type" in data:
                    data["patch_type"] = data["type"]
                elif "operation_type" in data:
                    data["patch_type"] = data["operation_type"]
                elif "op" in data:
                    data["patch_type"] = data["op"]
        return data

    @property
    def operation_type(self) -> PatchType:
        return self.patch_type


class ClauseVersion(BaseModel):
    model_config = ConfigDict(extra="allow")
    clause_id: str
    instrument: str
    version_number: int = 1
    text: str
    valid_from: str
    valid_to: Optional[str] = None
    applied_patches: List[PatchOperation] = []




