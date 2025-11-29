"""
BRICK 2 Database Configuration
==============================
Uses SQLAlchemy + SQLite for persistent storage of:
- Referrers & Commissions (BPO)
- Marketing Content History
- Lead Status
- System State
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use SQLite for simplicity and portability (file-based)
# In production, this can be swapped for PostgreSQL via connection string
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./brick2.db")

engine = create_engine(
    DB_PATH, 
    connect_args={"check_same_thread": False} if "sqlite" in DB_PATH else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI routes to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

