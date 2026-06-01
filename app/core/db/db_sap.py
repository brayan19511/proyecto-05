# app/core/db_sap.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_sap = create_engine(
    settings.DATABASE_URL_SAP,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SapSessionLocal = sessionmaker(
    bind=engine_sap,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

def get_db_sap():
    db = SapSessionLocal()
    try:
        yield db
    finally:
        db.close()