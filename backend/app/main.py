import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api import auth, business, schemes, recommendations, ocr, admin

# Setup logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables if they do not exist
try:
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas initialized.")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")

app = FastAPI(
    title=settings.APP_NAME,
    description="API for the MSME Government Scheme Recommendation Platform",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount APIRouters
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(business.router, prefix=f"{settings.API_V1_STR}/business", tags=["Business Profile"])
app.include_router(schemes.router, prefix=f"{settings.API_V1_STR}/schemes", tags=["Schemes"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recommendations", tags=["Recommendations"])
app.include_router(ocr.router, prefix=f"{settings.API_V1_STR}/ocr", tags=["Document OCR"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin Operations"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "docs_url": "/docs"
    }
