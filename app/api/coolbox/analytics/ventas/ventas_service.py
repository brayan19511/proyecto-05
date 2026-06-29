from datetime import date

from app.api.coolbox.analytics.common.validators import (
    normalize_list,
    normalize_optional,
    validate_date_range,
    validate_limit,
)
from app.api.coolbox.analytics.ventas.ventas_repository import (
    AnalyticsVentasRepository,
)


class AnalyticsVentasService:
    def __init__(self, db):
        self.repo = AnalyticsVentasRepository(db)

    def get_kpis(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        return self.repo.get_kpis(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=normalize_optional(canal),
            tiendas=normalize_list(tiendas),
        )

    def get_evolucion(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        return self.repo.get_evolucion(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=normalize_optional(canal),
            tiendas=normalize_list(tiendas),
        )

    def get_por_canal(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        tiendas: list[str] | None = None,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        return self.repo.get_por_canal(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tiendas=normalize_list(tiendas),
        )

    def get_por_tienda(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
        limit: int = 10,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=100)
        return self.repo.get_por_tienda(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=normalize_optional(canal),
            tiendas=normalize_list(tiendas),
            limit=limit,
        )

    def get_top_productos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
        limit: int = 10,
    ):
        validate_date_range(fecha_inicio, fecha_fin)
        validate_limit(limit, maximum=100)
        return self.repo.get_top_productos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=normalize_optional(canal),
            tiendas=normalize_list(tiendas),
            limit=limit,
        )

    def get_filtros(self):
        return self.repo.get_filtros()
