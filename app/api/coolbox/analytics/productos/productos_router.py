from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.coolbox.analytics.productos.productos_schemas import (
    ProductoABCItem,
    ProductoTopItem,
    ProductoBajoMovimientoItem,
    ProductoResumenCategoriaItem,
    ProductosFiltrosResponse,
)
from app.api.coolbox.analytics.productos.productos_service import (
    AnalyticsProductosService,
)
from app.core.db.db_postgres import get_db


router = APIRouter(
    tags=["Analytics - Productos"],
)


@router.get(
    "/abc",
    response_model=list[ProductoABCItem],
    status_code=status.HTTP_200_OK,
)
def get_productos_abc(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    rubro: Optional[str] = Query(default=None),
    familia: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db=Depends(get_db),
):
    service = AnalyticsProductosService(db)

    return service.get_abc(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
        rubro=rubro,
        familia=familia,
        limit=limit,
    )


@router.get(
    "/top",
    response_model=list[ProductoTopItem],
    status_code=status.HTTP_200_OK,
)
def get_top_productos(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    rubro: Optional[str] = Query(default=None),
    familia: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    service = AnalyticsProductosService(db)

    return service.get_top_productos(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
        rubro=rubro,
        familia=familia,
        limit=limit,
    )


@router.get(
    "/bajo-movimiento",
    response_model=list[ProductoBajoMovimientoItem],
    status_code=status.HTTP_200_OK,
)
def get_productos_bajo_movimiento(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    rubro: Optional[str] = Query(default=None),
    familia: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
):
    service = AnalyticsProductosService(db)

    return service.get_bajo_movimiento(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
        rubro=rubro,
        familia=familia,
        limit=limit,
    )


@router.get(
    "/por-rubro",
    response_model=list[ProductoResumenCategoriaItem],
    status_code=status.HTTP_200_OK,
)
def get_productos_por_rubro(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsProductosService(db)

    return service.get_por_rubro(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
    )


@router.get(
    "/por-familia",
    response_model=list[ProductoResumenCategoriaItem],
    status_code=status.HTTP_200_OK,
)
def get_productos_por_familia(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    canal: Optional[str] = Query(default=None),
    tienda: Optional[str] = Query(default=None),
    rubro: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    service = AnalyticsProductosService(db)

    return service.get_por_familia(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        canal=canal,
        tienda=tienda,
        rubro=rubro,
    )
@router.get(
    "/filtros",
    response_model=ProductosFiltrosResponse,
    status_code=status.HTTP_200_OK,
)
def get_filtros_productos(
    db=Depends(get_db),
):
    service = AnalyticsProductosService(db)
    return service.get_filtros()
