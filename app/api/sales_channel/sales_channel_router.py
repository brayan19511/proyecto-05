from fastapi import APIRouter

from app.api.sales_channel.peya import peya_router
from app.api.sales_channel.rappi import rappi_router


router = APIRouter(prefix="/sales-channels")
router.include_router(rappi_router.router)
router.include_router(peya_router.router)
