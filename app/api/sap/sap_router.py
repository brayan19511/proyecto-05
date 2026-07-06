from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.jobs.constants import JobType
from app.api.jobs.schemas import JobDetailResponse
from app.api.jobs.service import JobService
from app.api.sap.sap_schema import SapServiceDocumentos
from app.core.access import require_any_permission
from app.core.config import settings
from app.core.db.db_postgres import get_db
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
