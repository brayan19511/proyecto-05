from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from app.api.finance.payment_provider.email_job_processor import (
    PaymentProviderEmailJobProcessor,
)
from app.core.db.db_postgres import SessionLocal
from app.workers.celery_app import celery_app
from app.workers.common import retry_countdown


@celery_app.task(
    bind=True,
    name="jobs.payment_provider.send_email_batch",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=2,
    soft_time_limit=900,
    time_limit=960,
)
def process_payment_provider_email_batch(self, batch_id: str):
    """Envia correos de proveedores por lote y guarda avance en jobs."""
    parsed_batch_id = UUID(batch_id)
    with SessionLocal() as db:
        processor = PaymentProviderEmailJobProcessor(db)
        try:
            return processor.process(parsed_batch_id, self.request.id)
        except SoftTimeLimitExceeded:
            processor.mark_failed(
                parsed_batch_id,
                "El lote de correos excedio el tiempo permitido",
            )
            raise
        except Exception as exc:
            if self.request.retries >= self.max_retries:
                processor.mark_failed(
                    parsed_batch_id,
                    "Error inesperado durante el envio de correos",
                )
                raise
            raise self.retry(
                exc=exc,
                countdown=retry_countdown(self.request.retries, 180),
            )
