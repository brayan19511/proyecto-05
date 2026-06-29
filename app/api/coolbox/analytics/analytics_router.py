from fastapi import APIRouter, Depends

from app.api.coolbox.analytics.clientes import clientes_router
from app.api.coolbox.analytics.productos import productos_router
from app.api.coolbox.analytics.ventas import ventas_router
from app.api.security.api_client.api_client_auth import require_analytics_access



router = APIRouter(
    dependencies=[Depends(require_analytics_access)],
)


router.include_router(prefix="/ventas", router=ventas_router.router)
router.include_router(prefix="/productos", router=productos_router.router)
router.include_router(prefix="/clientes", router=clientes_router.router)
