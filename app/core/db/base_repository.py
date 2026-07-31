"""Repositorio base con las operaciones comunes de acceso a datos.

Evita repetir en cada repositorio el constructor, commit/rollback, alta de
entidades, búsqueda por id y el patrón de listado paginado. Las subclases solo
declaran el atributo de clase `model`.
"""

from typing import Generic, TypeVar

from sqlalchemy.orm import Query, Session


ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    # La subclase define el modelo ORM que maneja este repositorio.
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, entity_id) -> ModelT | None:
        """Busca por clave primaria."""
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        """Agrega la entidad a la sesión (sin commit)."""
        self.db.add(entity)
        return entity

    def paginate(
        self,
        query: Query,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ModelT], int]:
        """Devuelve (items, total) aplicando offset/limit sobre la consulta."""
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
