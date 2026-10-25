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
    limit: Optional[int] = Query(None, description="Limit the number of recommendations returned")
):
    """
    Fetches the ranked list of recommendations for the current MSME.
    Generates recommendations on-the-fly if not already created.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found."
        )
        
    query = db.query(Recommendation).options(
        joinedload(Recommendation.scheme)
    ).filter(
        Recommendation.user_id == current_user.user_id
    ).order_by(Recommendation.match_score.desc())
    
    if limit:
        query = query.limit(limit)
    
    recs = query.all()
    if not recs:
        recs = recommendation_engine.generate_recommendations(db, profile)
        if limit:
            recs = recs[:limit]
        
    explanation_updated = False
    for r in recs:
        if r.is_eligible and not r.recommendation_reason:
            try:
                if not r.scheme:
                    r.scheme = db.query(Scheme).filter(Scheme.id == r.scheme_id).first()
                r.recommendation_reason = rag_service.generate_explanation(profile, r.scheme, r.eligibility_reasons)
                explanation_updated = True
            except Exception:
                pass
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
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_444_NOT_FOUND,
            detail="Business profile not found."
        )
        
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
    benefit_taken = False
    
    for r in recs:
        scheme = r.scheme
        if not scheme:
            continue
        if r.is_eligible:
            if not benefit_taken:
                total_benefit = float(scheme.max_benefit_amount)
                benefit_taken = True
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

def _calculate_completion(profile: BusinessProfile) -> int:
    fields = [
        profile.company_name,
        profile.entity_type,
        profile.industry_type,
        profile.sector,
        profile.state,
        profile.district,
    ]
    filled = sum(1 for f in fields if f)
    # Add numerical turnover & investment checks
    if float(profile.annual_turnover) > 0:
        filled += 1
    if float(profile.investment_in_plant_machinery) > 0:
        filled += 1
    # Registrations check
    if profile.registrations:
        filled += 1
        
    return int((filled / 9) * 100)
