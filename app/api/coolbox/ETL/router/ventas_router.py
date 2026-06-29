"""Sales ETL execution endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.api.coolbox.ETL.service.ventas_service import VentasService
from app.core.db.db_coolbox import get_db_coolbox
from app.core.db.db_postgres import get_db


router = APIRouter(tags=["Procesamiento Ventas"])


@router.post("/procesar-ventas", status_code=status.HTTP_200_OK)
def procesar_ventas_por_fecha(
    fecha: date,
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db),
):
    """Reprocess one complete business date."""
    service = VentasService(db_fuente=db_fuente, db_destino=db_destino)
    return service.ejecutar_etl_ventas(fecha)


@router.post("/procesar-ventas-delta", status_code=status.HTTP_200_OK)
def procesar_ventas_automatico(
    dias_reproceso: int = Query(default=2, ge=1, le=31),
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db),
):
    """Reprocess today and the configured number of preceding Lima dates."""
    service = VentasService(db_fuente=db_fuente, db_destino=db_destino)
    return service.ejecutar_etl_ventas_automatico(
        dias_reproceso=dias_reproceso,
    )


@router.post("/procesar-ventas-rango", status_code=status.HTTP_200_OK)
def procesar_ventas_por_rango(
    fecha_inicio: date,
    fecha_fin: date,
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db),
):
    """Reprocess each date independently and return a per-day report."""
    service = VentasService(db_fuente=db_fuente, db_destino=db_destino)
    return service.ejecutar_etl_ventas_rango(fecha_inicio, fecha_fin)
