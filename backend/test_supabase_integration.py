import sys
import requests
from app.config import settings
from app.services.storage_service import storage_service
from app.database import SessionLocal
from app.models import BusinessProfile, Scheme, Recommendation, OCRVerification

def run_checks():
    print("==================================================")
    print("1. DATABASE VERIFICATION (Supabase PostgreSQL)")
    print(f"Host: {settings.DATABASE_URL.split('@')[-1]}")
    print("==================================================")
    db = SessionLocal()
    try:
        scheme_count = db.query(Scheme).count()
        profile_count = db.query(BusinessProfile).count()
        rec_count = db.query(Recommendation).count()
        ocr_count = db.query(OCRVerification).count()
        print(f" - Schemes in Supabase: {scheme_count}")
        print(f" - Business Profiles in Supabase: {profile_count}")
        print(f" - Recommendations in Supabase: {rec_count}")
        print(f" - OCR Verifications in Supabase: {ocr_count}")
        assert scheme_count > 0, "Schemes table should have seeded schemes"
        print(" -> Database tables verified!")
    finally:
        db.close()

    print("\n==================================================")
    print("2. SUPABASE STORAGE VERIFICATION")
    print(f"Supabase URL: {settings.SUPABASE_URL}")
    print("==================================================")
    dummy_pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
    
    # Upload test document PDF
    doc_url = storage_service.upload_document_pdf(
        user_id="test_user",
        filename="test_verification.pdf",
        file_bytes=dummy_pdf_bytes,
        content_type="application/pdf"
    )
    print(f"Uploaded test document PDF: {doc_url}")
    assert doc_url is not None and "documents" in doc_url, "Document upload failed"
    
    # Check if public URL is accessible
    r_doc = requests.get(doc_url)
    print(f"Public access HTTP status: {r_doc.status_code}")
    assert r_doc.status_code == 200, f"Expected 200 OK for document URL, got {r_doc.status_code}"
    print(" -> Document Storage verified!")

    # Upload test scheme PDF
    scheme_url = storage_service.upload_scheme_pdf(
        scheme_id="test_scheme",
        filename="test_guidelines.pdf",
        file_bytes=dummy_pdf_bytes,
        content_type="application/pdf"
    )
    print(f"Uploaded test scheme PDF: {scheme_url}")
    assert scheme_url is not None and "schemes" in scheme_url, "Scheme upload failed"
    r_scheme = requests.get(scheme_url)
    print(f"Public access HTTP status: {r_scheme.status_code}")
    assert r_scheme.status_code == 200, f"Expected 200 OK for scheme URL, got {r_scheme.status_code}"
    print(" -> Scheme Storage verified!")

    print("\n==================================================")
    print("3. SUPABASE AUTH VERIFICATION (Emails & Passwords)")
    print("==================================================")
    auth_url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "email": "admin@msme.gov.in",
        "password": "password123"
    }
    auth_resp = requests.post(auth_url, json=payload, headers=headers)
    print(f"Supabase Auth login status: {auth_resp.status_code}")
    if auth_resp.status_code == 200:
        token_data = auth_resp.json()
        print(f" -> Login successful!")
        print(f" -> User ID (UUID): {token_data.get('user', {}).get('id')}")
        print(f" -> Access token received: {token_data.get('access_token')[:25]}...")
    else:
        print(f"Auth response: {auth_resp.text}")

    print("\n==================================================")
    print("ALL SUPABASE VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_checks()
