import datetime
import uuid
from sqlalchemy import Column, String, Integer, Boolean, Numeric, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    entity_type = Column(String(100), nullable=True)  # Proprietorship, Partnership, Pvt Ltd, etc.
    industry_type = Column(String(100), nullable=True)  # Manufacturing, Service, Trading
    sector = Column(String(255), nullable=True)  # e.g., Textiles, IT, Food Processing
    annual_turnover = Column(Numeric(15, 2), default=0.0)
    investment_in_plant_machinery = Column(Numeric(15, 2), default=0.0)
    number_of_employees = Column(Integer, default=0)
    business_age_years = Column(Integer, default=0)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    social_category = Column(String(50), default="General")  # General, SC, ST, OBC
    gender_of_owner = Column(String(50), default="Male")  # Male, Female, Transgender
    is_minority_owned = Column(Boolean, default=False)
    registrations = Column(JSON, default=dict)  # {"gst": true, "udyam": true, "pan": true}
    project_title = Column(String(255), nullable=True)
    project_description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    recommendations = relationship("Recommendation", back_populates="business_profile", cascade="all, delete-orphan")
    ocr_verifications = relationship("OCRVerification", back_populates="business_profile", cascade="all, delete-orphan")


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    ministry = Column(String(255), nullable=False)
    funding_type = Column(String(100), nullable=True)  # Grant, Subsidy, Loan, Equity
    max_benefit_amount = Column(Numeric(15, 2), default=0.0)
    official_link = Column(String(512), nullable=True)
    pdf_storage_path = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Eligibility criteria JSON: e.g., 
    # {
    #   "max_turnover": 50000000, 
    #   "max_investment": 10000000, 
    #   "allowed_sectors": ["Manufacturing", "IT"], 
    #   "allowed_states": ["Delhi", "Maharashtra"],
    #   "min_business_age": 1,
    #   "allowed_owner_categories": ["SC", "ST", "Female"]
    # }
    eligibility_rules = Column(JSON, default=dict)
    required_documents = Column(JSON, default=list)  # ["Aadhaar", "PAN", "GST", "Udyam"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    recommendations = relationship("Recommendation", back_populates="scheme", cascade="all, delete-orphan")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False)
    scheme_id = Column(UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Numeric(5, 2), default=0.0)
    is_eligible = Column(Boolean, default=False)
    eligibility_reasons = Column(JSON, default=dict)  # Check logs: {"turnover": {"pass": true, "value": X, "limit": Y}}
    recommendation_reason = Column(Text, nullable=True)  # LLM explainable AI reason
    status = Column(String(50), default="Viewed")  # Viewed, Applied, Bookmarked
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    business_profile = relationship("BusinessProfile", back_populates="recommendations")
    scheme = relationship("Scheme", back_populates="recommendations")


class OCRVerification(Base):
    __tablename__ = "ocr_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(50), nullable=False)  # Aadhaar, PAN, GST, Udyam
    file_url = Column(String(512), nullable=True)
    extracted_data = Column(JSON, default=dict)
    verification_status = Column(String(50), default="Pending")  # Verified, Mismatched, Failed
    mismatch_details = Column(JSON, default=dict)
    verified_at = Column(DateTime, default=datetime.datetime.utcnow)

    business_profile = relationship("BusinessProfile", back_populates="ocr_verifications")
