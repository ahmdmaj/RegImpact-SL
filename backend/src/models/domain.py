from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class OutcomeStatus(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONDITIONAL_MISSING_DATA = "CONDITIONAL_MISSING_DATA"
    CONDITIONAL_RULE = "CONDITIONAL_RULE"
    UNSUPPORTED = "UNSUPPORTED"


class Product(BaseModel):
    category: Optional[str] = None
    prepackaged: Optional[bool] = None

class ProductionCapacity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    per_period: Optional[str] = None

class Premises(BaseModel):
    type: Optional[str] = None
    location_authority_area: Optional[str] = None

class Market(BaseModel):
    domestic: Optional[bool] = None
    import_flag: Optional[bool] = None
    export_flag: Optional[bool] = None

class BusinessProfile(BaseModel):
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
    instrument: str
    authority: str
    gazette_no: str
    clause: str
    page: int
    quote_span: str

class Validity(BaseModel):
    published: str
    commences: str
    transition_until: Optional[str] = None
    superseded_by: Optional[str] = None

class Condition(BaseModel):
    field: str
    op: str
    value: Any

class AppliesIf(BaseModel):
    all: List[Condition]

class Obligation(BaseModel):
    type: str
    text: str
    impact_categories: List[str]

class Verification(BaseModel):
    status: str
    extraction_model: str
    agreement: bool

class Rule(BaseModel):
    rule_id: str
    source: Source
    validity: Validity
    applies_if: AppliesIf
    exceptions: List[Any]
    obligation: Obligation
    verification: Verification
