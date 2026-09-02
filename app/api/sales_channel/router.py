from fastapi import APIRouter, Depends

from app.api.sales_channel.peya import router as peya_routes
from app.api.sales_channel.rappi import router as rappi_routes
from app.core.modules import MODULE_SALES_CHANNEL, ModuleEnabled


router = APIRouter(
    prefix="/sales-channels",
    dependencies=[Depends(ModuleEnabled(MODULE_SALES_CHANNEL))],
)
router.include_router(rappi_routes.router)
router.include_router(peya_routes.router)
