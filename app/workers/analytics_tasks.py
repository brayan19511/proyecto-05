from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded

from app.core.config import settings
from app.core.db.db_icg import get_icg_session_factory
from app.core.db.db_postgres import SessionLocal
from app.services.ingestion.processor import AnalyticsIngestionProcessor
from app.workers.celery_app import celery_app
from app.workers.common import BATCH_TIMEOUT_MESSAGE


@celery_app.task(
    bind=True,
    name="jobs.analytics.process_batch",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=2,
    soft_time_limit=settings.SAP_JOB_SOFT_TIME_LIMIT,
    time_limit=settings.SAP_JOB_TIME_LIMIT,
)
def process_analytics_batch(self, batch_id: str):
    parsed_batch_id = UUID(batch_id)
    icg_session_factory = get_icg_session_factory()

    with SessionLocal() as db_local, icg_session_factory() as db_icg:
        processor = AnalyticsIngestionProcessor(db_local, db_icg)
        try:
            return processor.process(parsed_batch_id, self.request.id)
        except SoftTimeLimitExceeded:
            processor.mark_failed(parsed_batch_id, BATCH_TIMEOUT_MESSAGE)
            raise
        except Exception:
            processor.mark_failed(
                parsed_batch_id,
                "Error inesperado durante la ingesta analytics",
            )
            raise
