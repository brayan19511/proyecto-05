from datetime import date

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy.orm import Session

from app.api.jobs.constants import JobType
from app.api.jobs.schemas import JobDetailResponse
from app.api.jobs.service import JobService
from app.api.sap.sap_schema import SapServiceDocumentos
from app.api.sap.service.sap_reconciliation_service import (
    SapReconciliationExcelService,
)
from app.core.access import require_any_permission
from app.core.config import settings
from app.core.db.db_postgres import get_db
from app.core.exceptions import ValidationError
from app.core.secret_cipher import encrypt_job_secrets
from app.workers.dispatcher import dispatch_job

router = APIRouter(prefix="/sap", tags=["SAP"])


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db, dispatcher=dispatch_job)


@router.post(
    "/services",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolar una operacion masiva de documentos SAP",
)
def service_sap(
    request: SapServiceDocumentos,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=100,
    ),
    service: JobService = Depends(get_job_service),
    current_user=Depends(require_any_permission("sap.execute")),
):
    # Este endpoint recibe una lista simple de documentos y crea una tarea
    # asincrona. La API responde rapido con job_id; el worker hace el trabajo.
    return service.create_job(
        job_type=JobType.SAP_DOCUMENT_ACTION.value,
        parameters={
            "database": request.database,
            "entity": request.entidad,
            "action": request.action,
        },
        references=request.documentos,
        user_id=current_user.id,
        batch_size=settings.SAP_JOB_BATCH_SIZE,
        idempotency_key=idempotency_key,
        encrypted_secrets=encrypt_job_secrets(
            {
                "user": request.user,
                "password": request.password.get_secret_value(),
            }
        ),
    )


@router.post(
    "/services-reconciliation",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolar una conciliacion interna masiva en SAP",
)
def service_sap_reconciliation(
    user: str = Form(...),
    password: str = Form(...),
    database: str = Form(...),
    recon_date: date | None = Form(default=None),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=100,
    ),
    service: JobService = Depends(get_job_service),
    current_user=Depends(require_any_permission("sap.execute")),
):
    normalized_user = user.strip()
    if not normalized_user:
        raise ValidationError("user es obligatorio")
    if not password:
        raise ValidationError("password es obligatorio")

    normalized_database = database.strip()
    if not normalized_database:
        raise ValidationError("database es obligatorio")

    # El Excel se transforma una sola vez aqui. Despues cada ReconNum queda
    # guardado como item del job y el worker ya no depende del archivo original.
    payloads = SapReconciliationExcelService().build_payloads(
        file.file,
        filename=file.filename,
        recon_date=recon_date or date.today(),
    )

    return service.create_job(
        job_type=JobType.SAP_RECONCILIATION.value,
        parameters={
            "database": normalized_database,
            "entity": "InternalReconciliations",
            "source": "excel",
            "filename": file.filename,
        },
        references=list(payloads.keys()),
        user_id=current_user.id,
        batch_size=settings.SAP_JOB_BATCH_SIZE,
        idempotency_key=idempotency_key,
        encrypted_secrets=encrypt_job_secrets(
            {
                "user": normalized_user,
                "password": password,
            }
        ),
        item_payloads=payloads,
    )
