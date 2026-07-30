"""Utilidades compartidas para crear sesiones de base de datos.

Centraliza la configuración de sessionmaker y el ciclo de vida de la sesión
por request, que antes se repetía en db_postgres/db_sap/db_cic/db_ofisis.
"""

from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones con la configuración estándar del proyecto.

    Sin autoflush ni autocommit, y sin expirar objetos tras el commit.
    """
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def session_scope(
    factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    """Abre una sesión por request y garantiza rollback ante error y cierre."""
    db = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
