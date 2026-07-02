from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_cic_engine() -> Engine:
    """Return the shared connection pool for the CIC SQL Server database."""
    return create_engine(
        settings.get_cic_database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.SQL_ECHO,
    )


@lru_cache
def get_cic_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_cic_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db_cic() -> Generator[Session, None, None]:
    """Open a request-scoped CIC session and always release its connection."""
    db = get_cic_session_factory()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
