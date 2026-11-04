from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# In production, Database URL is provided by Supabase / local Postgres
# We use echo=False in production to avoid cluttering logs
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Ensure proper DBAPI driver is selected if not explicitly given
if db_url.startswith("postgresql://") and "+" not in db_url.split("://")[0]:
    try:
        import psycopg2
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    except ImportError:
        try:
            import psycopg
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        except ImportError:
            pass

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
