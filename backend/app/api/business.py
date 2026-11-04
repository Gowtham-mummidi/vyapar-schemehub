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
    Creates a default blank profile if one does not exist yet.
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
        db.flush()
        
    # Update profile fields
    update_data = profile_data.model_dump(exclude_unset=True)

    # Sync project_title and project_description from registrations.projects if present
    regs = update_data.get("registrations") or profile.registrations or {}
    projs = regs.get("projects", [])
    if projs:
        if not update_data.get("project_title"):
            update_data["project_title"] = projs[0].get("title", "")
        if not update_data.get("project_description"):
            update_data["project_description"] = "\n".join(
                [f"{p.get('title', '')}: {p.get('description') or p.get('desc') or ''}" for p in projs]
            )

    for key, value in update_data.items():
        setattr(profile, key, value)
        
    import datetime
    from sqlalchemy.orm.attributes import flag_modified
    profile.updated_at = datetime.datetime.utcnow()
    flag_modified(profile, "registrations")

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
