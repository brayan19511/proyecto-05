from fastapi import APIRouter

from app.api.sales_channel.sku.router_factory import (
    build_managed_sku_router,
)
from app.api.sales_channel.channel_registry import RAPPI_MEXICO, RAPPI_PERU


router = APIRouter()
RAPPI_SKU_CONFIG = RAPPI_PERU.sku_config
MX_RAPPI_SKU_CONFIG = RAPPI_MEXICO.sku_config

router.include_router(
    build_managed_sku_router(
        prefix=RAPPI_PERU.sku_prefix,
        tag=f"Sales Channels - {RAPPI_PERU.display_name}",
        config=RAPPI_SKU_CONFIG,
    )
)
router.include_router(
    build_managed_sku_router(
        prefix=RAPPI_MEXICO.sku_prefix,
        tag=f"Sales Channels - {RAPPI_MEXICO.display_name}",
        config=MX_RAPPI_SKU_CONFIG,
    )
)
