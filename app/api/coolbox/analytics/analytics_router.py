from fastapi import APIRouter

from app.api.coolbox.analytics.clientes import clientes_router
from app.api.coolbox.analytics.productos import productos_router
from app.api.coolbox.analytics.ventas import ventas_router



router = APIRouter()


router.include_router(prefix="/ventas", router=ventas_router.router)
router.include_router(prefix="/productos", router=productos_router.router)
router.include_router(prefix="/clientes", router=clientes_router.router)
