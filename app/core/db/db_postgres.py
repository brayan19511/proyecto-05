from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import settings
from app.core.db.session import make_session_factory, session_scope


engine = create_engine(
    settings.DATABASE_URL_POSTGRES,
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
)

SessionLocal = make_session_factory(engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    yield from session_scope(SessionLocal)
