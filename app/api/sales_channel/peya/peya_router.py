from fastapi import APIRouter, Depends, Query, Response, status

from app.api.sales_channel.sku_schema import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
    BulkSkuSyncResponse,
    PeyaSkuResponse,
    PromoSkuCreateRequest,
    PromoSkuResponse,
    SkuCreateRequest,
    SkuUpdateRequest,
)
from app.api.sales_channel.sku_service import (
    ManagedSkuService,
    PromoSkuService,
    SkuModelConfig,
)
from app.core.access import require_any_permission
from app.core.db.db_ofisis import get_db_ofisis_ecomm
from app.models.external.ofisis.ecomm import PeyaPromoSku, PeyaSku


router = APIRouter(prefix="/peya", tags=["Sales Channels - Peya"])

PEYA_SKU_CONFIG = SkuModelConfig(
    model=PeyaSku,
    external_id_field="id_peya",
    updated_at_field="modified_at",
    channel_name="Peya",
    promotion_model=PeyaPromoSku,
)


def get_peya_sku_service(
    db=Depends(get_db_ofisis_ecomm),
) -> ManagedSkuService:
    return ManagedSkuService(db, PEYA_SKU_CONFIG)


def get_peya_promo_sku_service(
    db=Depends(get_db_ofisis_ecomm),
) -> PromoSkuService:
    return PromoSkuService(db, PeyaPromoSku, PeyaSku)


@router.get("/skus", response_model=list[PeyaSkuResponse])
def list_peya_skus(
    search: str | None = Query(default=None, max_length=255),
    active: bool | None = None,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.view"),
    ),
):
    return service.list(search, active)


@router.post("/skus/bulk-sync", response_model=BulkSkuSyncResponse)
def bulk_sync_peya_skus(
    request: BulkSkuSyncRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.bulk_sync(request)


@router.post("/skus/active-snapshot", response_model=BulkSkuSyncResponse)
def apply_peya_active_snapshot(
    request: ActiveSkuSnapshotRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.apply_active_snapshot(request)


@router.get("/skus/{sku}", response_model=PeyaSkuResponse)
def get_peya_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.view"),
    ),
):
    return service.get(sku)


@router.post(
    "/skus",
    response_model=PeyaSkuResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_peya_sku(
    request: SkuCreateRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.create(request)


@router.patch("/skus/{sku}", response_model=PeyaSkuResponse)
def update_peya_sku(
    sku: str,
    request: SkuUpdateRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.update(sku, request)


@router.post("/skus/{sku}/activate", response_model=PeyaSkuResponse)
def activate_peya_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.set_active(sku, True)


@router.post("/skus/{sku}/deactivate", response_model=PeyaSkuResponse)
def deactivate_peya_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.set_active(sku, False)


@router.get("/promo-skus", response_model=list[PromoSkuResponse])
def list_peya_promo_skus(
    search: str | None = Query(default=None, max_length=255),
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.view"),
    ),
):
    return service.list(search)


@router.get("/promo-skus/{sku}", response_model=PromoSkuResponse)
def get_peya_promo_sku(
    sku: str,
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.view"),
    ),
):
    return service.get(sku)


@router.post(
    "/promo-skus",
    response_model=PromoSkuResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_peya_promo_sku(
    request: PromoSkuCreateRequest,
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.create(request)


@router.delete(
    "/promo-skus/{sku}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_peya_promo_sku(
    sku: str,
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    service.delete(sku)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
