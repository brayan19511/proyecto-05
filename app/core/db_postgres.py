# app/core/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings

# Usamos la URL calculada de nuestros settings
engine = create_engine(settings.ASYNC_DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# El generador para la Inyección de Dependencias en FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()