from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)

from app.api.sales_channel.imports.schemas import SkuImportResponse
from app.api.sales_channel.imports.service import SkuExcelImportService
from app.api.sales_channel.permissions import (
    PROMOTION_EDIT_PERMISSION,
    PROMOTION_IMPORT_PERMISSION,
    PROMOTION_VIEW_PERMISSION,
)
from app.api.sales_channel.peya.promotion_service import PromoSkuService
from app.api.sales_channel.peya.schemas import (
    PromoSkuCreateRequest,
    PromoSkuResponse,
)
from app.core.access import require_any_permission
from app.core.db.db_ofisis import get_db_ofisis_ecomm
from app.models.external.ofisis.ecomm import PeyaPromoSku, PeyaSku


router = APIRouter(prefix="/promo-skus")


def get_peya_promo_sku_service(
    db=Depends(get_db_ofisis_ecomm),
) -> PromoSkuService:
    return PromoSkuService(db, PeyaPromoSku, PeyaSku)


@router.get("", response_model=list[PromoSkuResponse])
def list_peya_promo_skus(
    search: str | None = Query(default=None, max_length=255),
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(require_any_permission(PROMOTION_VIEW_PERMISSION)),
):
    return service.list(search)


@router.get("/{sku}", response_model=PromoSkuResponse)
def get_peya_promo_sku(
    sku: str,
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(require_any_permission(PROMOTION_VIEW_PERMISSION)),
):
    return service.get(sku)


@router.post(
    "",
    response_model=PromoSkuResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_peya_promo_sku(
    request: PromoSkuCreateRequest,
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(require_any_permission(PROMOTION_EDIT_PERMISSION)),
):
    return service.create(request)


@router.post("/import/preview", response_model=SkuImportResponse)
def preview_peya_promotion_import(
    file: UploadFile = File(...),
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    import_service: SkuExcelImportService = Depends(SkuExcelImportService),
    current_user=Depends(require_any_permission(PROMOTION_IMPORT_PERMISSION)),
):
    return import_service.preview_promotions(file, service)


@router.post("/import", response_model=SkuImportResponse)
def execute_peya_promotion_import(
    file: UploadFile = File(...),
    expected_sha256: str | None = Form(None),
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    import_service: SkuExcelImportService = Depends(SkuExcelImportService),
    current_user=Depends(require_any_permission(PROMOTION_IMPORT_PERMISSION)),
):
    return import_service.import_promotions(
        file,
        service,
        expected_sha256,
    )


@router.delete("/{sku}", status_code=status.HTTP_204_NO_CONTENT)
def delete_peya_promo_sku(
    sku: str,
    service: PromoSkuService = Depends(get_peya_promo_sku_service),
    current_user=Depends(require_any_permission(PROMOTION_EDIT_PERMISSION)),
):
    service.delete(sku)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
