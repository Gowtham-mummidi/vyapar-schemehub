import sys
import os

# Add backend root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing backend package imports...")
    
    # Configuration and db
    from app.config import settings
    from app.database import Base, get_db
    
    # Models
    from app.models import BusinessProfile, Scheme, Recommendation, OCRVerification
    
    # Schemas
    from app.schemas import TokenData, BusinessProfileOut, SchemeOut, ChatResponse
    
    # Core Services
    from app.services.eligibility_engine import eligibility_engine
    from app.services.recommendation_engine import recommendation_engine
    from app.services.rag_service import rag_service
    from app.services.embedding_service import embedding_service
    from app.services.ocr_service import ocr_service
    from app.services.ingestion_pipeline import ingestion_pipeline
    
    # FastAPI Application Entrypoint
    from app.main import app
    
    print("\n---------------------------------------------------------")
    print("VERIFICATION SUCCESS: All backend models, routers, and")
    print("services compile and resolve successfully!")
    print("---------------------------------------------------------")
    sys.exit(0)
except Exception as e:
    import traceback
    print("\n---------------------------------------------------------")
    print("VERIFICATION FAILED: Backend compilation or import error!")
    print("---------------------------------------------------------")
    traceback.print_exc()
    sys.exit(1)
