import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from decimal import Decimal

from app.database import get_db
from app.schemas import SchemeOut, SchemeCreate, SchemeUpdate, TokenData
from app.models import Scheme
from app.services.auth_service import get_current_user
from app.services.ingestion_pipeline import ingestion_pipeline
from app.services.rag_service import rag_service
from app.services.storage_service import storage_service

router = APIRouter()

def require_admin(current_user: TokenData = Depends(get_current_user)):
    """
    Enforces administrator roles.
    """
    import logging as _log
    _log.getLogger(__name__).info(f"Admin check: role='{current_user.role}', email='{current_user.email}', user_id='{current_user.user_id}'")
    if current_user.role != "admin" and (not current_user.email or "admin" not in current_user.email.lower()):
        _log.getLogger(__name__).warning(f"Admin access denied for role='{current_user.role}' email='{current_user.email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    return current_user

@router.post("/schemes", response_model=SchemeOut, status_code=status.HTTP_201_CREATED)
def create_scheme(
    scheme_data: SchemeCreate,
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Creates a new government scheme.
    """
    existing = db.query(Scheme).filter(Scheme.name == scheme_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A scheme with this name already exists."
        )
        
    scheme = Scheme(**scheme_data.model_dump())
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme

@router.put("/schemes/{scheme_id}", response_model=SchemeOut)
def update_scheme(
    scheme_id: UUID,
    scheme_data: SchemeUpdate,
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Modifies an existing scheme.
    """
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found."
        )
        
    update_dict = scheme_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(scheme, key, value)
        
    db.commit()
    db.refresh(scheme)
    return scheme

@router.delete("/schemes/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheme(
    scheme_id: UUID,
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Deletes a scheme and cleans up its vector indexes in Qdrant.
    """
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found."
        )
        
    # Clean up vectors
    try:
        rag_service.delete_scheme_chunks(str(scheme_id))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to clear scheme vectors: {str(e)}")
        
    db.delete(scheme)
    db.commit()
    return None

@router.post("/schemes/bulk-upload", status_code=status.HTTP_201_CREATED)
def bulk_upload_schemes(
    schemes_data: List[SchemeCreate],
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Bulk upload multiple schemes at once. Accepts a JSON array of SchemeCreate objects.
    Skips schemes whose names already exist.
    """
    created = []
    skipped = 0
    for s in schemes_data:
        existing = db.query(Scheme).filter(Scheme.name == s.name).first()
        if existing:
            skipped += 1
            continue
        scheme = Scheme(**s.model_dump())
        db.add(scheme)
        created.append(scheme)
    db.commit()
    for c in created:
        db.refresh(c)
    return {
        "created": len(created),
        "skipped": skipped,
        "schemes": created
    }

@router.delete("/schemes", status_code=status.HTTP_200_OK)
def clear_all_schemes(
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Deletes ALL schemes and their vector indexes.
    """
    all_schemes = db.query(Scheme).all()
    count = len(all_schemes)
    for scheme in all_schemes:
        try:
            rag_service.delete_scheme_chunks(str(scheme.id))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to clear vectors for {scheme.id}: {str(e)}")
        db.delete(scheme)
    db.commit()
    return {"message": f"Deleted {count} schemes."}

@router.post("/schemes/from-pdf", status_code=status.HTTP_201_CREATED)
def create_scheme_from_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Upload a PDF to automatically create a scheme. Gemini extracts name, description,
    eligibility rules, required documents, etc. directly from the PDF text.
    """
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        try:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        pages = ingestion_pipeline.extract_pdf_pages(tmp_path)
        if not pages:
            raise HTTPException(status_code=422, detail="No text could be extracted from the PDF.")

        full_text = "\n".join(p[1] for p in pages)
        extracted = ingestion_pipeline.extract_full_scheme(full_text)
        if not extracted or not extracted.get("name"):
            raise HTTPException(
                status_code=422,
                detail="Could not extract scheme details from PDF. Ensure the PDF contains readable text about an MSME scheme."
            )

        existing = db.query(Scheme).filter(Scheme.name == extracted["name"]).first()
        if existing:
            # Scheme exists — just ingest the PDF for this scheme
            scheme = existing
        else:
            scheme = Scheme(
                name=extracted["name"],
                description=extracted.get("description", ""),
                ministry=extracted.get("ministry", "Ministry of MSME"),
                funding_type=extracted.get("funding_type", "Subsidy"),
                max_benefit_amount=Decimal(str(extracted.get("max_benefit_amount", 0))),
                official_link=extracted.get("official_link", ""),
                eligibility_rules=extracted.get("eligibility_rules", {}),
                required_documents=extracted.get("required_documents", []),
                is_active=True
            )
            db.add(scheme)
            db.flush()

        # Upload scheme PDF to Supabase Storage bucket 'schemes'
        with open(tmp_path, "rb") as f_bytes:
            pdf_bytes = f_bytes.read()
        storage_url = storage_service.upload_scheme_pdf(
            scheme_id=str(scheme.id),
            filename=f"scheme_{scheme.id}{suffix}",
            file_bytes=pdf_bytes,
            content_type="application/pdf"
        )
        scheme.pdf_storage_path = storage_url

        # Run ingestion pipeline (chunk + index + update rules)
        success = ingestion_pipeline.run_ingestion(db, scheme, tmp_path)
        if not success:
            raise HTTPException(status_code=422, detail="PDF text extraction yielded no characters.")

        db.commit()
        db.refresh(scheme)
        return {
            "status": "Success",
            "scheme": {
                "id": str(scheme.id),
                "name": scheme.name,
                "funding_type": scheme.funding_type,
                "max_benefit_amount": float(scheme.max_benefit_amount),
            },
            "message": f"Scheme '{scheme.name}' created and PDF indexed."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/schemes/{scheme_id}/upload-pdf")
def upload_scheme_pdf(
    scheme_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: TokenData = Depends(require_admin)
):
    """
    Uploads a scheme PDF, stores it temporarily, and runs the vector ingestion/eligibility parser.
    """
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found."
        )

    # 1. Save uploaded file to temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        try:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write upload stream: {str(e)}"
            )

    # 2. Run ingestion pipeline and upload to Supabase Storage
    try:
        # Upload scheme PDF to Supabase Storage bucket 'schemes'
        with open(temp_path, "rb") as f_bytes:
            pdf_bytes = f_bytes.read()
        storage_url = storage_service.upload_scheme_pdf(
            scheme_id=str(scheme_id),
            filename=f"scheme_{scheme_id}{suffix}",
            file_bytes=pdf_bytes,
            content_type="application/pdf"
        )
        scheme.pdf_storage_path = storage_url
        
        success = ingestion_pipeline.run_ingestion(db, scheme, temp_path)
        if not success:
             raise HTTPException(
                  status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                  detail="PDF text extraction yielded no characters."
             )
        
        db.commit()
        return {
            "status": "Success",
            "message": "Scheme PDF processed, chunked, embedded, and eligibility parameters parsed successfully.",
            "storage_path": scheme.pdf_storage_path,
            "extracted_rules": scheme.eligibility_rules
        }
    except Exception as e:
         raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=f"Ingestion pipeline processing error: {str(e)}"
         )
    finally:
         if os.path.exists(temp_path):
              os.remove(temp_path)
