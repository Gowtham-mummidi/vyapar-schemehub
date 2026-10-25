from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None

# Business Profile Schemas
class BusinessProfileBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    entity_type: Optional[str] = None
    industry_type: Optional[str] = None
    sector: Optional[str] = None
    annual_turnover: Decimal = Field(default=Decimal("0.0"))
    investment_in_plant_machinery: Decimal = Field(default=Decimal("0.0"))
    number_of_employees: int = 0
    business_age_years: int = 0
    state: Optional[str] = None
    district: Optional[str] = None
    social_category: str = "General"
    gender_of_owner: str = "Male"
    is_minority_owned: bool = False
    registrations: Dict[str, bool] = Field(default_factory=dict)
    project_title: Optional[str] = None
    project_description: Optional[str] = None

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfileUpdate(BusinessProfileBase):
    pass

class BusinessProfileOut(BusinessProfileBase):
    id: UUID
    updated_at: datetime

    class Config:
        from_attributes = True

# Scheme Schemas
class SchemeBase(BaseModel):
    name: str
    description: str
    ministry: str
    funding_type: Optional[str] = None
    max_benefit_amount: Decimal = Field(default=Decimal("0.0"))
    official_link: Optional[str] = None
    pdf_storage_path: Optional[str] = None
    is_active: bool = True
    eligibility_rules: Dict[str, Any] = Field(default_factory=dict)
    required_documents: List[str] = Field(default_factory=list)

class SchemeCreate(SchemeBase):
    pass

class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ministry: Optional[str] = None
    funding_type: Optional[str] = None
    max_benefit_amount: Optional[Decimal] = None
    official_link: Optional[str] = None
    pdf_storage_path: Optional[str] = None
    is_active: Optional[bool] = None
    eligibility_rules: Optional[Dict[str, Any]] = None
    required_documents: Optional[List[str]] = None

class SchemeOut(SchemeBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Recommendation Schemas
class RecommendationOut(BaseModel):
    id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    scheme_id: UUID
    scheme: SchemeOut
    match_score: Decimal
    match_percentage: Optional[float] = None
    is_eligible: bool = True
    eligibility_reasons: Dict[str, Any] = Field(default_factory=dict)
    recommendation_reason: Optional[str] = None
    status: str = "Viewed"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecommendationStatusUpdate(BaseModel):
    status: str

class AISchemeSearchQuery(BaseModel):
    query: str
    funding_type: Optional[str] = "All"
    limit: Optional[int] = 50

# OCR Verification Schemas
class OCRVerificationOut(BaseModel):
    id: UUID
    user_id: UUID
    document_type: str
    file_url: Optional[str] = None
    extracted_data: Dict[str, Any]
    verification_status: str
    mismatch_details: Dict[str, Any]
    verified_at: datetime

    class Config:
        from_attributes = True

# Chat Schemas
class ChatQuery(BaseModel):
    message: str
    scheme_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
