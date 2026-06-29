from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)

from app.api.sales_channel.channel_registry import PEYA_PERU
from app.api.sales_channel.imports.schemas import (
    SkuImportMode,
    SkuImportResponse,
)
from app.api.sales_channel.imports.service import SkuExcelImportService
from app.api.sales_channel.permissions import (
    SKU_EDIT_PERMISSION,
    SKU_IMPORT_PERMISSION,
    SKU_VIEW_PERMISSION,
)
from app.api.sales_channel.peya.schemas import PeyaSkuResponse
from app.api.sales_channel.sku.schemas import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
    BulkSkuSyncResponse,
    SkuCreateRequest,
    SkuUpdateRequest,
)
from app.api.sales_channel.sku.service import ManagedSkuService
from app.core.access import require_any_permission
from app.core.db.db_ofisis import get_db_ofisis_ecomm


router = APIRouter(prefix="/skus")
PEYA_SKU_CONFIG = PEYA_PERU.sku_config


def get_peya_sku_service(
    db=Depends(get_db_ofisis_ecomm),
) -> ManagedSkuService:
    return ManagedSkuService(db, PEYA_SKU_CONFIG)


@router.get("", response_model=list[PeyaSkuResponse])
def list_peya_skus(
    search: str | None = Query(default=None, max_length=255),
    active: bool | None = None,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_VIEW_PERMISSION)),
):
    return service.list(search, active)


@router.post("/bulk-sync", response_model=BulkSkuSyncResponse)
def bulk_sync_peya_skus(
    request: BulkSkuSyncRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_IMPORT_PERMISSION)),
):
    return service.bulk_sync(request)


@router.post("/active-snapshot", response_model=BulkSkuSyncResponse)
def apply_peya_active_snapshot(
    request: ActiveSkuSnapshotRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_IMPORT_PERMISSION)),
):
    return service.apply_active_snapshot(request)


@router.post("/import/preview", response_model=SkuImportResponse)
def preview_peya_sku_import(
    file: UploadFile = File(...),
    mode: SkuImportMode = Form(...),
    create_missing: bool = Form(True),
    service: ManagedSkuService = Depends(get_peya_sku_service),
    import_service: SkuExcelImportService = Depends(SkuExcelImportService),
    current_user=Depends(require_any_permission(SKU_IMPORT_PERMISSION)),
):
    return import_service.preview_managed(
        file,
        mode,
        create_missing,
        service,
    )


@router.post("/import", response_model=SkuImportResponse)
def execute_peya_sku_import(
    file: UploadFile = File(...),
    mode: SkuImportMode = Form(...),
    create_missing: bool = Form(True),
    expected_sha256: str | None = Form(None),
    service: ManagedSkuService = Depends(get_peya_sku_service),
    import_service: SkuExcelImportService = Depends(SkuExcelImportService),
    current_user=Depends(require_any_permission(SKU_IMPORT_PERMISSION)),
):
    return import_service.import_managed(
        file,
        mode,
        create_missing,
        service,
        expected_sha256,
    )


@router.get("/{sku}", response_model=PeyaSkuResponse)
def get_peya_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_VIEW_PERMISSION)),
):
    return service.get(sku)


@router.post(
    "",
    response_model=PeyaSkuResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_peya_sku(
    request: SkuCreateRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_EDIT_PERMISSION)),
):
    return service.create(request)


@router.patch("/{sku}", response_model=PeyaSkuResponse)
def update_peya_sku(
    sku: str,
    request: SkuUpdateRequest,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_EDIT_PERMISSION)),
):
    return service.update(sku, request)


@router.post("/{sku}/activate", response_model=PeyaSkuResponse)
def activate_peya_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_EDIT_PERMISSION)),
):
    return service.set_active(sku, True)


@router.post("/{sku}/deactivate", response_model=PeyaSkuResponse)
def deactivate_peya_sku(
    sku: str,
    service: ManagedSkuService = Depends(get_peya_sku_service),
    current_user=Depends(require_any_permission(SKU_EDIT_PERMISSION)),
):
    return service.set_active(sku, False)
