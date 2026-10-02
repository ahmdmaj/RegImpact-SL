from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
from .business import BusinessProfile

class Scenario(BaseModel):
    scenario_id: str
    business_id: str
    business_profile: Optional[BusinessProfile] = None
    regulation_id: str
    regulatory_event: Optional[str] = None
    question: str
    expected_applicability: str
    applicability_reason: Optional[str] = None
    expected_obligation: Optional[List[str]] = Field(default_factory=list)
    expected_impact: Optional[str] = None
    expected_action: Optional[str] = None
    evidence_reference: Optional[str] = None
    effective_date: Optional[date] = None
    difficulty: Optional[str] = None
    scenario_type: Optional[str] = None
