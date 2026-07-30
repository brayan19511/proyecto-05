"""Schemas base reutilizables para toda la API.

Centraliza tres piezas que antes se repetían en cada módulo:
- ORMModel: respuestas que se construyen desde modelos ORM.
- PageResponse: forma estándar de un listado paginado.
- PaginationParams: parámetros limit/offset comunes.
"""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class ORMModel(BaseModel):
    """Base para *Response que se leen directo de un modelo ORM."""

    model_config = ConfigDict(from_attributes=True)


class PageResponse(BaseModel, Generic[T]):
    """Listado paginado estándar. Usar PageResponse[MiSchema] como tipo."""

    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def build(
        cls,
        items: list[T],
        total: int,
        limit: int,
        offset: int,
    ) -> "PageResponse[T]":
        """Arma la página calculando has_more a partir de total y offset."""
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )


class PaginationParams:
    """Parámetros de paginación reutilizables como dependencia de FastAPI.

    Se instancia con los límites propios de cada endpoint, por ejemplo:
        Depends(PaginationParams(default_limit=50, max_limit=200))
    """

    def __init__(self, *, default_limit: int = 50, max_limit: int = 200):
        self.default_limit = default_limit
        self.max_limit = max_limit

    def __call__(
        self,
        limit: int | None = Query(default=None, ge=1),
        offset: int = Query(default=0, ge=0),
    ) -> "Pagination":
        resolved = self.default_limit if limit is None else min(limit, self.max_limit)
        return Pagination(limit=resolved, offset=offset)


class Pagination(BaseModel):
    """Valores de paginación ya resueltos."""

    limit: int
    offset: int
