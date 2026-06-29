# app/api/coolbox/tiendas/tiendas_router.py

from fastapi import APIRouter, Depends, status

from app.api.coolbox.ETL.service.tiendas_service import TiendasService
from app.core.db.db_postgres import get_db
from app.core.db.db_coolbox import get_db_coolbox


router = APIRouter(
    tags=["Coolbox - Tiendas"],
)


@router.post(
    "/sincronizar",
    status_code=status.HTTP_200_OK,
)
async def sincronizar_tiendas(
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db),
):
    service = TiendasService(
        db_fuente=db_fuente,
        db_destino=db_destino,
    )

    return service.ejecutar_etl_tiendas()
