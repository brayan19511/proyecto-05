from fastapi import APIRouter

from app.api.sales_channel.peya import router as peya_routes
from app.api.sales_channel.rappi import router as rappi_routes


router = APIRouter(prefix="/sales-channels")
router.include_router(rappi_routes.router)
router.include_router(peya_routes.router)
