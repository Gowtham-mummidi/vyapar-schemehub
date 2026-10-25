import os
import sys
from dotenv import load_dotenv

# Add backend root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environmental configurations
load_dotenv()

from app.database import engine, Base
# Ensure all models are registered
from app.models import BusinessProfile, Scheme, Recommendation, OCRVerification

def init_supabase_tables():
    print("-----------------------------------------------------------------")
    print(f"Connecting to database: {engine.url.host}")
    print("-----------------------------------------------------------------")
    try:
        # Create all tables in the Supabase PostgreSQL instance
        Base.metadata.create_all(bind=engine)
        print("MIGRATION SUCCESS: All SQL schemas successfully initialized on Supabase!")
        print("Tables created:")
        for table_name in Base.metadata.tables.keys():
            print(f" - {table_name}")
        print("-----------------------------------------------------------------")
    except Exception as e:
        print("MIGRATION FAILED: Unable to establish database connection or build tables.")
        print(f"Details: {str(e)}")
        print("Please check database password or internet connectivity.")
        print("-----------------------------------------------------------------")
        sys.exit(1)

if __name__ == "__main__":
    init_supabase_tables()
