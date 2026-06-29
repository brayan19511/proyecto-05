from datetime import date

from app.api.coolbox.analytics.clientes.clientes_repository import (
    AnalyticsClientesRepository,
)
from app.api.coolbox.analytics.common.validators import (
    normalize_optional,
    validate_date_range,
    validate_limit,
)


class AnalyticsClientesService:
    def __init__(self, db):
        self.repo = AnalyticsClientesRepository(db)

    def _filters(
        self,
        canal: str | None,
        tienda: str | None,
    ) -> dict:
        return {
            "canal": normalize_optional(canal),
            "tienda": normalize_optional(tienda),
        }

    def get_rfm(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 100,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=500)
        return self.repo.get_rfm(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            **self._filters(canal, tienda),
        )

    def get_segmentos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        return self.repo.get_segmentos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            **self._filters(canal, tienda),
        )

    def get_top_clientes(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=100)
        return self.repo.get_top_clientes(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            **self._filters(canal, tienda),
        )

    def get_frecuencia_compra(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=100)
        return self.repo.get_frecuencia_compra(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            **self._filters(canal, tienda),
        )

    def get_filtros(self):
        return self.repo.get_filtros()
