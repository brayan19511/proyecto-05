from datetime import date

from app.api.coolbox.analytics.common.validators import (
    normalize_optional,
    validate_date_range,
    validate_limit,
)
from app.api.coolbox.analytics.productos.productos_repository import (
    AnalyticsProductosRepository,
)


class AnalyticsProductosService:
    def __init__(self, db):
        self.repo = AnalyticsProductosRepository(db)

    def _base_filters(
        self,
        canal: str | None,
        tienda: str | None,
        rubro: str | None = None,
        familia: str | None = None,
    ) -> dict:
        return {
            "canal": normalize_optional(canal),
            "tienda": normalize_optional(tienda),
            "rubro": normalize_optional(rubro),
            "familia": normalize_optional(familia),
        }

    def get_abc(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
        limit: int = 100,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=500)
        return self.repo.get_abc(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            **self._base_filters(canal, tienda, rubro, familia),
        )

    def get_top_productos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
        limit: int = 10,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=100)
        return self.repo.get_top_productos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            **self._base_filters(canal, tienda, rubro, familia),
        )

    def get_bajo_movimiento(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
        limit: int = 10,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=100)
        return self.repo.get_bajo_movimiento(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            **self._base_filters(canal, tienda, rubro, familia),
        )

    def get_por_rubro(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        filters = self._base_filters(canal, tienda)
        return self.repo.get_por_rubro(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=filters["canal"],
            tienda=filters["tienda"],
        )

    def get_por_familia(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        filters = self._base_filters(canal, tienda, rubro)
        return self.repo.get_por_familia(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=filters["canal"],
            tienda=filters["tienda"],
            rubro=filters["rubro"],
        )

    def get_filtros(self):
        return self.repo.get_filtros()
