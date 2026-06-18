from fastapi import APIRouter

from app.api.coolbox.analytics import analytics_router
from app.api.coolbox.ventas import ventas_router

router = APIRouter()


router.include_router(prefix="/ventas", router=ventas_router.router)
router.include_router(prefix="/analytics", router=analytics_router.router)
