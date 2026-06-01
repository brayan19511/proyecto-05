from fastapi import APIRouter

from app.api.coolbox.ventas import ventas_router

router = APIRouter()


router.include_router(prefix="/ventas", router=ventas_router.router)
