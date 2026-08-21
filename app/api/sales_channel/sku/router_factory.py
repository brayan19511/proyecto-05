from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.sales_channel.imports.service import SkuExcelImportService
from app.api.sales_channel.permissions import (
    SKU_EDIT_PERMISSION,
    SKU_IMPORT_PERMISSION,
    SKU_VIEW_PERMISSION,
)
from app.api.sales_channel.imports.schemas import (
    SkuImportMode,
    SkuImportResponse,
)
from app.api.sales_channel.sku.schemas import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
    BulkSkuSyncResponse,
    SkuCreateRequest,
    SkuResponse,
    SkuUpdateRequest,
)
from app.api.sales_channel.imports.icg_enrichment import IcgDescriptionLookup
from app.api.sales_channel.sku.service import ManagedSkuService, SkuModelConfig
from app.core.access import require_any_permission
from app.core.db.db_icg import get_icg_session_factory
from app.core.db.db_ofisis import get_db_ofisis_ecomm
from app.core.db.session import session_scope


def build_managed_sku_router(
    *,
    prefix: str,
    tag: str,
    config: SkuModelConfig,
    icg_database: str | None = None,
) -> APIRouter:
    """Build the standard CRUD and synchronization contract for one channel.

    Providers with the same SKU behavior reuse these routes while supplying a
    different model configuration from ``channel_registry``.

    ``icg_database`` indica la base ICG (segun el pais) desde la que se lee el
    nombre del articulo en el preview. Si es None, no se enriquece.
    """
    router = APIRouter(prefix=prefix, tags=[tag])

    def get_service(
        db=Depends(get_db_ofisis_ecomm),
    ) -> ManagedSkuService:
        return ManagedSkuService(db, config)

    def get_icg_session():
        # Sesion ICG del pais del canal. Si el canal no tiene base ICG
        # configurada (p. ej. Mexico sin conexion), no se abre nada.
        if not icg_database:
            yield None
            return
        yield from session_scope(get_icg_session_factory(icg_database))

    @router.get("", response_model=list[SkuResponse])
    def list_skus(
        search: str | None = Query(default=None, max_length=255),
        active: bool | None = None,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_VIEW_PERMISSION),
        ),
    ):
        return service.list(search, active)

    @router.post("/bulk-sync", response_model=BulkSkuSyncResponse)
    def bulk_sync_skus(
        request: BulkSkuSyncRequest,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_IMPORT_PERMISSION),
        ),
    ):
        return service.bulk_sync(request)

    @router.post("/active-snapshot", response_model=BulkSkuSyncResponse)
    def apply_active_snapshot(
        request: ActiveSkuSnapshotRequest,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_IMPORT_PERMISSION),
        ),
    ):
        return service.apply_active_snapshot(request)

    @router.post("/import/preview", response_model=SkuImportResponse)
    def preview_sku_import(
        file: UploadFile = File(...),
        mode: SkuImportMode = Form(...),
        create_missing: bool = Form(True),
        service: ManagedSkuService = Depends(get_service),
        import_service: SkuExcelImportService = Depends(
            SkuExcelImportService
        ),
        icg_db=Depends(get_icg_session),
        current_user=Depends(
            require_any_permission(SKU_IMPORT_PERMISSION),
        ),
    ):
        # El preview muestra el nombre del articulo (ICG del pais) junto a cada SKU.
        icg_lookup = IcgDescriptionLookup(icg_db) if icg_db is not None else None
        return import_service.preview_managed(
            file,
            mode,
            create_missing,
            service,
            icg_lookup=icg_lookup,
        )

    @router.post("/import", response_model=SkuImportResponse)
    def execute_sku_import(
        file: UploadFile = File(...),
        mode: SkuImportMode = Form(...),
        create_missing: bool = Form(True),
        expected_sha256: str | None = Form(None),
        service: ManagedSkuService = Depends(get_service),
        import_service: SkuExcelImportService = Depends(
            SkuExcelImportService
        ),
        current_user=Depends(
            require_any_permission(SKU_IMPORT_PERMISSION),
        ),
    ):
        return import_service.import_managed(
            file,
            mode,
            create_missing,
            service,
            expected_sha256,
        )

    @router.get("/{sku}", response_model=SkuResponse)
    def get_sku(
        sku: str,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_VIEW_PERMISSION),
        ),
    ):
        return service.get(sku)

    @router.post(
        "",
        response_model=SkuResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_sku(
        request: SkuCreateRequest,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_EDIT_PERMISSION),
        ),
    ):
        return service.create(request)

    @router.patch("/{sku}", response_model=SkuResponse)
    def update_sku(
        sku: str,
        request: SkuUpdateRequest,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_EDIT_PERMISSION),
        ),
    ):
        return service.update(sku, request)

    @router.post("/{sku}/activate", response_model=SkuResponse)
    def activate_sku(
        sku: str,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_EDIT_PERMISSION),
        ),
    ):
        return service.set_active(sku, True)

    @router.post("/{sku}/deactivate", response_model=SkuResponse)
    def deactivate_sku(
        sku: str,
        service: ManagedSkuService = Depends(get_service),
        current_user=Depends(
            require_any_permission(SKU_EDIT_PERMISSION),
        ),
    ):
        return service.set_active(sku, False)

    return router
