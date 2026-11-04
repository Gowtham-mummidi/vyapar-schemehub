from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import TokenData, BusinessProfileOut
from app.services.auth_service import get_current_user
from app.models import BusinessProfile

router = APIRouter()

@router.get("/me", response_model=BusinessProfileOut)
def get_me(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the current authenticated user's business profile.
    If no business profile exists yet (first-time login), creates one.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    
    import datetime
    if not profile:
        # Create a default blank profile for the new authenticated user
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
            registrations={},
            updated_at=datetime.datetime.utcnow()
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        changed = False
        if (not profile.name or profile.name == "User") and current_user.name and current_user.name != "User":
            profile.name = current_user.name
            changed = True
        if profile.updated_at is None:
            profile.updated_at = datetime.datetime.utcnow()
            changed = True
        if changed:
            db.commit()
            db.refresh(profile)
        
    return profile
