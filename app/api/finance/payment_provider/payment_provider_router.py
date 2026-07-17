import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)

from app.api.jobs.schemas import JobDetailResponse
from app.api.finance.payment_provider.payment_provider_schema import (
    PaymentProviderCreateRequest,
    PaymentProviderResponse,
    PaymentProviderUpdateRequest,
)
from app.api.finance.payment_provider.payment_provider_service import (
    PaymentProviderService,
)
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payment_provider",
    tags=["PAYMENT PROVIDER"],
)


def get_payment_provider_service(db=Depends(get_db)) -> PaymentProviderService:
    return PaymentProviderService(db)


@router.get("/health")
async def health_check():
    logger.info("Health check endpoint called.")
    return {"status": "Payment provider service is healthy."}


@router.get("/providers", response_model=list[PaymentProviderResponse])
def list_providers(
    search: str | None = None,
    active: bool | None = None,
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.view", "payment_provider.edit"),
    ),
):
    return service.list_providers(search=search, active=active)


@router.post("/providers", response_model=PaymentProviderResponse)
def create_provider(
    request: PaymentProviderCreateRequest,
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(require_any_permission("payment_provider.edit")),
):
    return service.create_provider(request, current_user.id)


@router.get("/providers/{provider_id}", response_model=PaymentProviderResponse)
def get_provider(
    provider_id: UUID,
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.view", "payment_provider.edit"),
    ),
):
    return service.get_provider(provider_id)


@router.patch("/providers/{provider_id}", response_model=PaymentProviderResponse)
def update_provider(
    provider_id: UUID,
    request: PaymentProviderUpdateRequest,
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(require_any_permission("payment_provider.edit")),
):
    return service.update_provider(provider_id, request, current_user.id)


@router.delete("/providers/{provider_id}")
def delete_provider(
    provider_id: UUID,
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(require_any_permission("payment_provider.edit")),
):
    return service.delete_provider(provider_id, current_user.id)


@router.post("/process_payment", deprecated=True)
async def process_payment(
    files: list[UploadFile] = File(...),
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.process", "payment_provider.edit"),
    ),
):
    if not files:
        raise HTTPException(status_code=400, detail="Debe adjuntar al menos un PDF")

    resultado = service.process_files(files)
    return {
        "status": "Payment files processed.",
        **resultado,
    }


@router.post("/payments/preview")
async def preview_payments(
    files: list[UploadFile] = File(...),
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.process", "payment_provider.edit"),
    ),
):
    if not files:
        raise HTTPException(status_code=400, detail="Debe adjuntar al menos un PDF")

    return service.preview_files(files)


@router.post("/payments/renamed-zip")
async def download_renamed_zip(
    files: list[UploadFile] = File(...),
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.process", "payment_provider.edit"),
    ),
):
    if not files:
        raise HTTPException(status_code=400, detail="Debe adjuntar al menos un PDF")

    filename, content = service.build_renamed_zip(files)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/payments/send")
async def send_payment_emails(
    files: list[UploadFile] = File(...),
    mailing_parameter_id: int | None = Form(default=None),
    mailing_parameter_name: str | None = Form(default=None),
    subject_override: str | None = Form(default=None),
    message_override: str | None = Form(default=None),
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.process", "payment_provider.edit"),
    ),
):
    if not files:
        raise HTTPException(status_code=400, detail="Debe adjuntar al menos un PDF")

    return service.send_payment_emails(
        files,
        mailing_parameter_id=mailing_parameter_id,
        mailing_parameter_name=mailing_parameter_name,
        subject_override=subject_override,
        message_override=message_override,
    )


@router.post("/payments/send-async", response_model=JobDetailResponse)
async def enqueue_payment_emails(
    files: list[UploadFile] = File(...),
    mailing_parameter_id: int | None = Form(default=None),
    mailing_parameter_name: str | None = Form(default=None),
    subject_override: str | None = Form(default=None),
    message_override: str | None = Form(default=None),
    batch_size: int = Form(default=10),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: PaymentProviderService = Depends(get_payment_provider_service),
    current_user=Depends(
        require_any_permission("payment_provider.process", "payment_provider.edit"),
    ),
):
    if not files:
        raise HTTPException(status_code=400, detail="Debe adjuntar al menos un PDF")

    return service.enqueue_payment_emails(
        files,
        current_user_id=current_user.id,
        mailing_parameter_id=mailing_parameter_id,
        mailing_parameter_name=mailing_parameter_name,
        subject_override=subject_override,
        message_override=message_override,
        idempotency_key=idempotency_key,
        batch_size=batch_size,
    )
