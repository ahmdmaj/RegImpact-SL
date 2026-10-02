from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any, Dict
from datetime import date

class RegulationRecord(BaseModel):
    regulation_id: str
    title: str
    authority: str
    gazette_number: Optional[str] = None
    domain: str
    publication_date: Optional[date] = None
    effective_date: Optional[date] = None
    status: str
    previous_versions: Optional[List[str]] = Field(default_factory=list)
    applicability_conditions: Optional[List[str]] = Field(default_factory=list)
    obligations: Optional[List[str]] = Field(default_factory=list)
    business_context_variables: Optional[List[str]] = Field(default_factory=list)
    source_url: Optional[str] = None
    evidence_note: Optional[str] = None
