from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.db.session import make_session_factory, session_scope


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
    return make_session_factory(get_ofisis_engine(database))


def get_db_ofisis(database: str) -> Generator[Session, None, None]:
    """Open one transactional session for the duration of a request."""
    yield from session_scope(get_ofisis_session_factory(database))


def get_db_ofisis_ecomm() -> Generator[Session, None, None]:
    """FastAPI dependency for the Ofisis EcommDB database."""
    yield from get_db_ofisis(settings.DB_OFISIS_ECOMM_DATABASE)
