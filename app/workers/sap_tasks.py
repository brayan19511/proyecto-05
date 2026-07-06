from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from app.api.sap.service.sap_job_service import SapJobProcessor
from app.core.config import settings
from app.core.db.db_postgres import SessionLocal
from app.core.exceptions import SAPConnectionError
from app.workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="jobs.sap.process_batch",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
    soft_time_limit=settings.SAP_JOB_SOFT_TIME_LIMIT,
    time_limit=settings.SAP_JOB_TIME_LIMIT,
)
def process_sap_batch(self, batch_id: str):
    """Run one retryable SAP batch; business state remains in PostgreSQL."""
    parsed_batch_id = UUID(batch_id)
    with SessionLocal() as db:
        processor = SapJobProcessor(db)
        try:
            return processor.process(parsed_batch_id, self.request.id)
        except SAPConnectionError as exc:
            error = "SAP no responde; el lote sera reintentado"
            if self.request.retries >= self.max_retries:
                processor.mark_failed(parsed_batch_id, error)
                raise
            processor.mark_retrying(parsed_batch_id, error)
            raise self.retry(
                exc=exc,
                countdown=min(30 * (2 ** self.request.retries), 300),
            )
        except SoftTimeLimitExceeded:
            processor.mark_failed(
                parsed_batch_id,
                "El lote excedio el tiempo permitido",
            )
            raise
        except Exception:
            processor.mark_failed(
                parsed_batch_id,
                "Error inesperado durante el procesamiento",
            )
            raise
