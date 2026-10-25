import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.config import settings

print("--- CONFIG DIAGNOSTIC ---")
print(f"App Name: {settings.APP_NAME}")
print(f"Gemini API Key present: {settings.GEMINI_API_KEY != 'placeholder_gemini_key'}")
print(f"Gemini Key prefix: {settings.GEMINI_API_KEY[:10] if settings.GEMINI_API_KEY else 'None'}")
print(f"Qdrant Host: {settings.QDRANT_HOST}")
print(f"Qdrant Key present: {settings.QDRANT_API_KEY is not None}")
print(f"Database Host: {settings.DATABASE_URL.split('@')[-1] if settings.DATABASE_URL else 'None'}")
print("-------------------------")
