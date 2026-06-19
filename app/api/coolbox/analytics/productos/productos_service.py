from datetime import date

from fastapi import HTTPException, status

from app.api.coolbox.analytics.productos.productos_repository import (
    AnalyticsProductosRepository,
)


class AnalyticsProductosService:
    def __init__(self, db):
        self.repo = AnalyticsProductosRepository(db)

    def _validar_fechas(self, fecha_inicio: date, fecha_fin: date):
        if fecha_inicio > fecha_fin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor a la fecha fin.",
            )

    def _validar_limit(self, limit: int):
        if limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El límite debe ser mayor a cero.",
            )

        if limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El límite máximo permitido es 100.",
            )

    def get_abc(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_abc(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
            rubro=rubro,
            familia=familia,
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
        self._validar_fechas(fecha_inicio, fecha_fin)
        self._validar_limit(limit)

        return self.repo.get_top_productos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
            rubro=rubro,
            familia=familia,
            limit=limit,
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
        self._validar_fechas(fecha_inicio, fecha_fin)
        self._validar_limit(limit)

        return self.repo.get_bajo_movimiento(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
            rubro=rubro,
            familia=familia,
            limit=limit,
        )

    def get_por_rubro(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_por_rubro(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
        )

    def get_por_familia(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_por_familia(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
            rubro=rubro,
        )
    def get_filtros(self):
        return self.repo.get_filtros()