from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from uuid import UUID
from app.database import get_db
from app.schemas import RecommendationOut, RecommendationStatusUpdate, TokenData
from app.models import Recommendation, BusinessProfile, Scheme
from app.services.auth_service import get_current_user
from app.services.recommendation_engine import recommendation_engine
from app.services.rag_service import rag_service

router = APIRouter()

@router.get("", response_model=List[RecommendationOut])
def get_user_recommendations(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    limit: Optional[int] = Query(None, description="Limit the number of recommendations returned"),
    refresh: bool = Query(False, description="Force recalculation of recommendations")
):
    """
    Fetches the ranked list of recommendations for the current MSME.
    Generates recommendations on-the-fly if not already created, or if new schemes have been added.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        user_name = current_user.name or (current_user.email.split('@')[0] if current_user.email else "User")
        profile = BusinessProfile(
            id=current_user.user_id,
            email=current_user.email,
            name=user_name,
            company_name="My Business",
            annual_turnover=0.0,
            investment_in_plant_machinery=0.0,
            number_of_employees=0,
            business_age_years=0,
            social_category="General",
            gender_of_owner="Male",
            is_minority_owned=False,
            registrations={}
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    active_schemes_count = db.query(Scheme).filter(Scheme.is_active == True).count()
    
    query = db.query(Recommendation).options(
        joinedload(Recommendation.scheme)
    ).filter(
        Recommendation.user_id == current_user.user_id
    ).order_by(Recommendation.match_score.desc())
    
    recs = query.all()
    # If no recommendations, or forced refresh, or new schemes registered that aren't yet in recommendations
    if not recs or refresh or len(recs) < active_schemes_count:
        recs = recommendation_engine.generate_recommendations(db, profile)
        
    if limit:
        recs = recs[:limit]
        
    explanation_updated = False
    for r in recs:
        # Populate match_percentage from match_score for schema serialization
        if getattr(r, 'match_percentage', None) is None:
            r.match_percentage = float(r.match_score or 0.0)

        # Only generate RAG explanation when reason is completely missing
        # and avoid overwriting the structured reason set by generate_recommendations
        if r.is_eligible and not r.recommendation_reason:
            try:
                if not r.scheme:
                    r.scheme = db.query(Scheme).filter(Scheme.id == r.scheme_id).first()
                r.recommendation_reason = rag_service.generate_explanation(profile, r.scheme, r.eligibility_reasons)
                explanation_updated = True
            except Exception:
                # Fallback: build a simple reason from the score and eligibility
                score = float(r.match_score or 0)
                r.recommendation_reason = f"✨ {int(round(score))}% Match: Eligible based on your business profile."
    if explanation_updated:
        db.commit()
        
    return recs

@router.put("/{rec_id}/status", response_model=RecommendationOut)
def update_recommendation_status(
    rec_id: UUID,
    payload: RecommendationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Updates the application state (Viewed, Applied, Bookmarked) of a scheme recommendation.
    """
    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id,
        Recommendation.user_id == current_user.user_id
    ).first()
    
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
        
    rec.status = payload.status
    db.commit()
    db.refresh(rec)
    return rec

@router.get("/analytics")
def get_recommendation_analytics(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Returns high-level statistics for the user dashboard:
    - Number of eligible schemes vs total
    - Total maximum benefit amount claimable
    - Scheme types (Subsidies, Loans, Grants) distribution
    - Missing documents list across all highly matching schemes
    - Accurate business profile completion percentage
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        user_name = current_user.name or (current_user.email.split('@')[0] if current_user.email else "User")
        profile = BusinessProfile(
            id=current_user.user_id,
            email=current_user.email,
            name=user_name,
            company_name="My Business",
            annual_turnover=0.0,
            investment_in_plant_machinery=0.0,
            number_of_employees=0,
            business_age_years=0,
            social_category="General",
            gender_of_owner="Male",
            is_minority_owned=False,
            registrations={}
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    recs = db.query(Recommendation).options(
        joinedload(Recommendation.scheme)
    ).filter(Recommendation.user_id == current_user.user_id).all()
    if not recs:
        recs = recommendation_engine.generate_recommendations(db, profile)
        
    eligible_count = sum(1 for r in recs if r.is_eligible)
    total_count = len(recs)
    
    total_benefit = 0.0
    scheme_types = {"Subsidy": 0, "Loan": 0, "Grant": 0, "Equity": 0, "Guarantee": 0}
    missing_docs = set()
    
    for r in recs:
        scheme = r.scheme
        if not scheme:
            continue
        if r.is_eligible:
            if scheme.max_benefit_amount:
                try:
                    total_benefit += float(scheme.max_benefit_amount)
                except (ValueError, TypeError):
                    pass
            ftype = scheme.funding_type or "Subsidy"
            scheme_types[ftype] = scheme_types.get(ftype, 0) + 1
                
        if float(r.match_score) >= 70.0:
            req_docs = scheme.required_documents or []
            user_regs = profile.registrations or {}
            for doc in req_docs:
                doc_key = doc.lower().strip()
                if not user_regs.get(doc_key, False):
                    missing_docs.add(doc)
                        
    return {
        "eligible_schemes_count": eligible_count,
        "total_schemes_analyzed": total_count,
        "total_potential_benefit": total_benefit,
        "funding_distribution": scheme_types,
        "critical_missing_documents": list(missing_docs),
        "profile_completion_percentage": _calculate_completion(profile)
    }

def _calculate_completion(profile: Optional[BusinessProfile]) -> int:
    if not profile:
        return 0

    score = 0
    # 1. Company identity (25 points max)
    cname = (profile.company_name or "").strip()
    if cname and cname != "My Business":
        score += 15
    elif cname:
        score += 5

    if profile.entity_type and profile.entity_type.strip():
        score += 5
    if profile.sector and profile.sector.strip() and profile.sector != "Other":
        score += 5
    elif profile.sector and profile.sector.strip():
        score += 3

    # 2. Financials & Size (25 points max)
    try:
        turnover = float(profile.annual_turnover or 0)
        investment = float(profile.investment_in_plant_machinery or 0)
    except (ValueError, TypeError):
        turnover, investment = 0.0, 0.0
        
    if turnover > 0:
        score += 10
    if investment > 0:
        score += 10
    if (profile.number_of_employees or 0) > 0 or (profile.business_age_years or 0) > 0:
        score += 5

    # 3. Location & Demographics (20 points max)
    if profile.state and profile.state.strip():
        score += 5
    if profile.district and profile.district.strip():
        score += 5
    if profile.social_category and profile.social_category.strip():
        score += 5
    if profile.gender_of_owner and profile.gender_of_owner.strip():
        score += 5

    # 4. Project Concept / AI Semantic Profile (15 points max)
    regs = profile.registrations or {}
    projs = regs.get("projects", [])
    if projs or (profile.project_title and profile.project_title.strip()):
        score += 15

    # 5. Registrations & Verified Docs (15 points max)
    reg_flags = [k for k, v in regs.items() if k != "projects" and bool(v)]
    if reg_flags:
        score += min(15, len(reg_flags) * 5)
    
    return min(score, 100)
