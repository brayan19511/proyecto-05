from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.coolbox.analytics.clientes.clientes_schemas import (
    ClienteRfmItem,
    ClienteSegmentoItem,
    ClienteTopItem,
    ClienteFrecuenciaCompraItem,
)
from app.api.coolbox.analytics.clientes.clientes_service import (
    AnalyticsClientesService,
)
from app.core.db.db_postgres import get_db


router = APIRouter(
    tags=["Analytics - Clientes"],
)


@router.get(
    "/rfm",
    response_model=list[ClienteRfmItem],
    status_code=status.HTTP_200_OK,
)
async def get_clientes_rfm(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsClientesService(db)

    return service.get_rfm(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
    )


@router.get(
    "/segmentos",
    response_model=list[ClienteSegmentoItem],
    status_code=status.HTTP_200_OK,
)
async def get_clientes_segmentos(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsClientesService(db)

    return service.get_segmentos(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
    )


@router.get(
    "/top",
    response_model=list[ClienteTopItem],
    status_code=status.HTTP_200_OK,
)
async def get_top_clientes(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    service = AnalyticsClientesService(db)

    return service.get_top_clientes(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
        limit=limit,
    )


@router.get(
    "/frecuencia-compra",
    response_model=list[ClienteFrecuenciaCompraItem],
    status_code=status.HTTP_200_OK,
)
async def get_clientes_frecuencia_compra(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    service = AnalyticsClientesService(db)

    return service.get_frecuencia_compra(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
        limit=limit,
    )