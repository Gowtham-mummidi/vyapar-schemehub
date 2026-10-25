import os
import shutil
import tempfile
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import OCRVerificationOut, TokenData
from app.models import OCRVerification, BusinessProfile
from app.services.auth_service import get_current_user
from app.services.ocr_service import ocr_service
from app.services.storage_service import storage_service

router = APIRouter()

@router.post("/verify", response_model=OCRVerificationOut)
def verify_document_upload(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Uploads a business document (Aadhaar, PAN, GST, Udyam) to run OCR checks,
    detect discrepancies, and update profile registrations on verification success.
    """
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == current_user.user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found. Complete profile details first."
        )

    # Validate document type parameter
    doc_type_clean = document_type.upper().strip()
    if doc_type_clean not in ["AADHAAR", "PAN", "GST", "UDYAM"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document type. Allowed types: Aadhaar, PAN, GST, Udyam"
        )

    # 1. Save uploaded file temporarily for parsing
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        try:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read upload stream: {str(e)}"
            )

    try:
        # 2. Upload file to Supabase Storage
        with open(temp_path, "rb") as f_bytes:
            content_bytes = f_bytes.read()
        
        content_type = file.content_type or ("application/pdf" if suffix.lower() == ".pdf" else "image/jpeg")
        doc_filename = f"{doc_type_clean.lower()}_{uuid.uuid4().hex[:8]}{suffix}"
        storage_url = storage_service.upload_document_pdf(
            user_id=profile.id,
            filename=doc_filename,
            file_bytes=content_bytes,
            content_type=content_type
        )

        # 3. Run OCR & parse details
        status_result, extracted, mismatches = ocr_service.verify_document(
            temp_path, doc_type_clean, profile
        )
        
        # 4. Create database record with Supabase Storage file_url
        verification = OCRVerification(
            user_id=profile.id,
            document_type=doc_type_clean,
            file_url=storage_url,
            extracted_data=extracted,
            verification_status=status_result,
            mismatch_details=mismatches
        )
        db.add(verification)
        
        # 4. If status is Verified or Mismatched (has data), we update registrations dictionary
        # In a real pipeline, we update the registration state if it is successfully 'Verified'.
        if status_result in ["Verified", "Mismatched"]:
            regs = dict(profile.registrations or {})
            key = doc_type_clean.lower()
            regs[key] = (status_result == "Verified")
            profile.registrations = regs
            
        db.commit()
        db.refresh(verification)
        db.refresh(profile)
        
        return verification
        
    except Exception as e:
         db.rollback()
         raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=f"Verification pipeline error: {str(e)}"
         )
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
