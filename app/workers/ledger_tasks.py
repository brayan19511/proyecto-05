from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from app.api.finance.libro_mayor.service.libro_mayor_job_processor import (
    LibroMayorJobProcessor,
)
from app.core.config import settings
from app.core.db.db_postgres import SessionLocal
from app.workers.celery_app import celery_app
from app.workers.common import BATCH_TIMEOUT_MESSAGE


@celery_app.task(
    bind=True,
    name="jobs.ledger.process_batch",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=2,
    soft_time_limit=settings.SAP_JOB_SOFT_TIME_LIMIT,
    time_limit=settings.SAP_JOB_TIME_LIMIT,
)
def process_ledger_batch(self, batch_id: str):
    """Procesa un lote de libro mayor; cada item es una cuenta en un dia."""
    parsed_batch_id = UUID(batch_id)
    from app.core.db.db_sap import SapSessionLocal

    with SessionLocal() as db_local, SapSessionLocal() as db_sap:
        processor = LibroMayorJobProcessor(db_local, db_sap)
        try:
            return processor.process(parsed_batch_id, self.request.id)
        except SoftTimeLimitExceeded:
            processor.mark_failed(parsed_batch_id, BATCH_TIMEOUT_MESSAGE)
            raise
        except Exception:
            processor.mark_failed(
                parsed_batch_id,
                "Error inesperado durante el procesamiento de libro mayor",
            )
            raise
