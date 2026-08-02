from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.db.session import make_session_factory, session_scope


@lru_cache
def get_icg_engine() -> Engine:
    return create_engine(
        settings.get_icg_database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.SQL_ECHO,
    )


@lru_cache
def get_icg_session_factory() -> sessionmaker[Session]:
    return make_session_factory(get_icg_engine())


def get_db_icg() -> Generator[Session, None, None]:
    yield from session_scope(get_icg_session_factory())
