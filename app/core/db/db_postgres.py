# app\core\db\db_postgres.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings

# A bounded pool reuses expensive cloud connections without overwhelming a
# small database plan with unbounded concurrent sessions.
engine = create_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

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
