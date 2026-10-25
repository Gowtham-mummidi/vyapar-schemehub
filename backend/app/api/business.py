from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import TokenData, BusinessProfileUpdate, BusinessProfileOut
from app.services.auth_service import get_current_user
from app.models import BusinessProfile
from app.services.recommendation_engine import recommendation_engine

router = APIRouter()

@router.get("/profile", response_model=BusinessProfileOut)
def get_business_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches the profile for the authenticated user.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found. Please log in or trigger auth handshake."
        )
    return profile

@router.put("/profile", response_model=BusinessProfileOut)
def update_business_profile(
    profile_data: BusinessProfileUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the business profile and triggers recommendation engine score recalculation.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found."
        )
        
    # Update profile fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    db.commit()
    db.refresh(profile)
    
    # Recalculate recommendations in the background/sync
    try:
        recommendation_engine.generate_recommendations(db, profile)
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logging.getLogger(__name__).error(f"Error generating recommendations after update: {str(e)}")
        
    return profile
