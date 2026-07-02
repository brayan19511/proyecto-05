from fastapi import APIRouter

from app.api.sales_channel.channel_registry import PEYA_PERU
from app.api.sales_channel.peya import promotion_router, sku_router


router = APIRouter(
    prefix=PEYA_PERU.base_prefix,
    tags=[f"Sales Channels - {PEYA_PERU.display_name}"],
)
router.include_router(sku_router.router)
router.include_router(promotion_router.router)
