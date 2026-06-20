from datetime import date

from fastapi import HTTPException, status

from app.api.coolbox.analytics.ventas.ventas_repository import (
    AnalyticsVentasRepository,
)


class AnalyticsVentasService:
    def __init__(self, db):
        self.repo = AnalyticsVentasRepository(db)

    def _validar_fechas(self, fecha_inicio: date, fecha_fin: date):
        if fecha_inicio > fecha_fin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor a la fecha fin.",
            )

    def _normalizar_tiendas(self, tiendas: list[str] | None):
        if not tiendas:
            return None

        tiendas_limpias = [
            tienda.strip()
            for tienda in tiendas
            if tienda and tienda.strip()
        ]

        return tiendas_limpias or None

    def get_kpis(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_kpis(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tiendas=self._normalizar_tiendas(tiendas),
        )

    def get_evolucion(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_evolucion(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tiendas=self._normalizar_tiendas(tiendas),
        )

    def get_por_canal(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        tiendas: list[str] | None = None,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

        return self.repo.get_por_canal(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tiendas=self._normalizar_tiendas(tiendas),
        )

    def get_por_tienda(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        limit: int = 10,
    ):
        self._validar_fechas(fecha_inicio, fecha_fin)

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

        return self.repo.get_por_tienda(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
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
        self._validar_fechas(fecha_inicio, fecha_fin)

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

        return self.repo.get_top_productos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            canal=canal,
            tiendas=self._normalizar_tiendas(tiendas),
            limit=limit,
        )

    def get_filtros(self):
        return self.repo.get_filtros()