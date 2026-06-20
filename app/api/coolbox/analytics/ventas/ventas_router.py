from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.coolbox.analytics.ventas.ventas_schemas import (
    VentasKpisResponse,
    VentasEvolucionItem,
    VentasPorCanalItem,
    VentasPorTiendaItem,
    TopProductoItem,
    VentasFiltrosResponse,
)
from app.api.coolbox.analytics.ventas.ventas_service import (
    AnalyticsVentasService,
)
from app.core.db.db_postgres import get_db


router = APIRouter(
    tags=["Analytics - Ventas"],
)


@router.get(
    "/kpis",
    response_model=VentasKpisResponse,
    status_code=status.HTTP_200_OK,
)
async def get_kpis_ventas(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tiendas: list[str] | None = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsVentasService(db)

    return service.get_kpis(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tiendas=tiendas,
    )


@router.get(
    "/evolucion",
    response_model=list[VentasEvolucionItem],
    status_code=status.HTTP_200_OK,
)
async def get_evolucion_ventas(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tiendas: list[str] | None = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsVentasService(db)

    return service.get_evolucion(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tiendas=tiendas,
    )


@router.get(
    "/por-canal",
    response_model=list[VentasPorCanalItem],
    status_code=status.HTTP_200_OK,
)
async def get_ventas_por_canal(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    tiendas: list[str] | None = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsVentasService(db)

    return service.get_por_canal(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tiendas=tiendas,
    )


@router.get(
    "/por-tienda",
    response_model=list[VentasPorTiendaItem],
    status_code=status.HTTP_200_OK,
)
async def get_ventas_por_tienda(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    service = AnalyticsVentasService(db)

    return service.get_por_tienda(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        limit=limit,
    )


@router.get(
    "/top-productos",
    response_model=list[TopProductoItem],
    status_code=status.HTTP_200_OK,
)
async def get_top_productos_ventas(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tiendas: list[str] | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    service = AnalyticsVentasService(db)

    return service.get_top_productos(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tiendas=tiendas,
        limit=limit,
    )


@router.get(
    "/filtros",
    response_model=VentasFiltrosResponse,
    status_code=status.HTTP_200_OK,
)
async def get_filtros_ventas(
    db=Depends(get_db),
):
    service = AnalyticsVentasService(db)
    return service.get_filtros()