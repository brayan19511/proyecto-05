from datetime import date

from fastapi import HTTPException, status

from app.api.coolbox.analytics.clientes.clientes_repository import (
    AnalyticsClientesRepository,
)


class AnalyticsClientesService:
    def __init__(self, db):
        self.repo = AnalyticsClientesRepository(db)

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

    def get_rfm(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_rfm(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
        )

    def get_segmentos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_segmentos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
        )

    def get_top_clientes(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)
        self._validar_limit(limit)

        return self.repo.get_top_clientes(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
            limit=limit,
        )

    def get_frecuencia_compra(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)
        self._validar_limit(limit)

        return self.repo.get_frecuencia_compra(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tienda=tienda,
            limit=limit,
        )