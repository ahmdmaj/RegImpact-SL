from pydantic import BaseModel
from typing import List, Optional

class BusinessProfile(BaseModel):
    business_id: str
    industry: Optional[str] = None
    product: Optional[List[str]] = None
    employees: Optional[int] = None
    production_capacity: Optional[str] = None
    production_unit: Optional[str] = None
    packaging: Optional[List[str]] = None
    market: Optional[List[str]] = None
    import_activity: Optional[bool] = None
    export_activity: Optional[bool] = None
    premises: Optional[str] = None
    location: Optional[str] = None
    revenue_band: Optional[str] = None
    environmental_activity: Optional[List[str]] = None
    existing_registrations: Optional[List[str]] = None
