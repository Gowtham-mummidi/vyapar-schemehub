from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.schemas import SchemeOut, ChatQuery, ChatResponse, TokenData, AISchemeSearchQuery, RecommendationOut
from app.models import Scheme, BusinessProfile
from app.services.auth_service import get_current_user, get_optional_current_user
from app.services.rag_service import rag_service
from app.services.ai_search_service import ai_search_service

router = APIRouter()

@router.get("", response_model=List[SchemeOut])
def list_schemes(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Lists all active government schemes.
    """
    schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
    return schemes

@router.get("/{scheme_id}", response_model=SchemeOut)
def get_scheme(
    scheme_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Retrieves details for a specific scheme.
    """
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id, Scheme.is_active == True).first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found or inactive."
        )
    return scheme

@router.post("/ai-search", response_model=List[RecommendationOut])
def ai_search_schemes(
    payload: AISchemeSearchQuery,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    AI-powered scheme matching & search.
    Calculates dynamic match percentage (0 - 100%) based on query intent and user's business profile.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    return ai_search_service.search_and_match(
        db=db,
        query=payload.query,
        profile=profile,
        funding_type=payload.funding_type or "All",
        limit=payload.limit or 50
    )

@router.post("/chat", response_model=ChatResponse)
def chatbot_general(
    query: ChatQuery,
    current_user: Optional[TokenData] = Depends(get_optional_current_user)
):
    """
    General purpose chatbot. Queries vector space and answers questions regarding MSME schemes.
    """
    res = rag_service.answer_query(query.message, scheme_id=query.scheme_id)
    return ChatResponse(
        response=res["response"],
        sources=res["sources"]
    )
