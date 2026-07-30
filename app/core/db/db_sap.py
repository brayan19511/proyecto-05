# app/core/db/db_sap.py

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db.session import make_session_factory, session_scope


engine_sap = create_engine(
    settings.DATABASE_URL_SAP,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.SQL_ECHO,
)

SapSessionLocal = make_session_factory(engine_sap)


def get_db_sap() -> Generator[Session, None, None]:
    yield from session_scope(SapSessionLocal)
