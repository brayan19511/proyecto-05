"""Product catalog synchronization endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.coolbox.ETL.service.productos_service import ProductosService
from app.core.db.db_coolbox import get_db_coolbox
from app.core.db.db_postgres import get_db


router = APIRouter(tags=["Procesamiento Productos"])


@router.post("/sincronizar", status_code=status.HTTP_200_OK)
def sincronizar_productos(
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db),
):
    """Upsert the current source product catalog into the warehouse."""
    service = ProductosService(
        db_fuente=db_fuente,
        db_destino=db_destino,
    )
    return service.ejecutar_etl_productos()
