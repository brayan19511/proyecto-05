from fastapi import APIRouter, Depends, Query, status

from app.api.sales_channel.sku_schema import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
    BulkSkuSyncResponse,
    SkuCreateRequest,
    SkuResponse,
    SkuUpdateRequest,
)
from app.api.sales_channel.sku_service import (
    ManagedSkuService,
    SkuModelConfig,
)
from app.core.access import require_any_permission
from app.core.db.db_ofisis import get_db_ofisis_ecomm
from app.models.external.ofisis.ecomm import RappiSku


router = APIRouter(prefix="/rappi/skus", tags=["Sales Channels - Rappi"])

RAPPI_SKU_CONFIG = SkuModelConfig(
    model=RappiSku,
    external_id_field="id_rappi",
    updated_at_field="updated_at",
    channel_name="Rappi",
)


def get_rappi_sku_service(
    db=Depends(get_db_ofisis_ecomm),
) -> ManagedSkuService:
    return ManagedSkuService(db, RAPPI_SKU_CONFIG)


@router.get("", response_model=list[SkuResponse])
def list_rappi_skus(
    search: str | None = Query(default=None, max_length=255),
    active: bool | None = None,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.view"),
    ),
):
    return service.list(search, active)


@router.post("/bulk-sync", response_model=BulkSkuSyncResponse)
def bulk_sync_rappi_skus(
    request: BulkSkuSyncRequest,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.bulk_sync(request)


@router.post("/active-snapshot", response_model=BulkSkuSyncResponse)
def apply_rappi_active_snapshot(
    request: ActiveSkuSnapshotRequest,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.apply_active_snapshot(request)


@router.get("/{sku}", response_model=SkuResponse)
def get_rappi_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.view"),
    ),
):
    return service.get(sku)


@router.post("", response_model=SkuResponse, status_code=status.HTTP_201_CREATED)
def create_rappi_sku(
    request: SkuCreateRequest,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.create(request)


@router.patch("/{sku}", response_model=SkuResponse)
def update_rappi_sku(
    sku: str,
    request: SkuUpdateRequest,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.update(sku, request)


@router.post("/{sku}/activate", response_model=SkuResponse)
def activate_rappi_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.set_active(sku, True)


@router.post("/{sku}/deactivate", response_model=SkuResponse)
def deactivate_rappi_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_rappi_sku_service),
    current_user=Depends(
        require_any_permission("sales_channels.skus.edit"),
    ),
):
    return service.set_active(sku, False)
