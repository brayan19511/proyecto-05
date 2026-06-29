from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_ofisis_engine(database: str) -> Engine:
    """Return one connection-pool engine for each configured database."""
    return create_engine(
        settings.get_ofisis_database_url(database),
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.SQL_ECHO,
    )


@lru_cache
def get_ofisis_session_factory(database: str) -> sessionmaker[Session]:
    """Reuse the session configuration associated with each engine."""
    return sessionmaker(
        bind=get_ofisis_engine(database),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db_ofisis(database: str) -> Generator[Session, None, None]:
    """Open one transactional session for the duration of a request."""
    db = get_ofisis_session_factory(database)()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_ofisis_ecomm() -> Generator[Session, None, None]:
    """FastAPI dependency for the Ofisis EcommDB database."""
    yield from get_db_ofisis(settings.DB_OFISIS_ECOMM_DATABASE)
