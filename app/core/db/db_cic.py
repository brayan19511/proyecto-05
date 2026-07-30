from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.db.session import make_session_factory, session_scope


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
    return make_session_factory(get_cic_engine())


def get_db_cic() -> Generator[Session, None, None]:
    """Open a request-scoped CIC session and always release its connection."""
    yield from session_scope(get_cic_session_factory())
