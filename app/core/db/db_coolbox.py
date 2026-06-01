# app\core\db\db_coolbox.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_coolbox = create_engine(
    settings.ASYNC_DATABASE_ICG_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

CoolboxSessionLocal = sessionmaker(
    bind=engine_coolbox,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

def get_db_coolbox():
    db = CoolboxSessionLocal()
    try:
        yield db
    finally:
        db.close()