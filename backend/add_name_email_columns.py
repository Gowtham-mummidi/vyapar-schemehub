import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in .env")
    sys.exit(1)

from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS name VARCHAR(255)"))
    conn.execute(text("ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
    conn.commit()
    print("Columns 'name' and 'email' added to business_profiles table.")
