from app.api.scheduled_jobs.service import ScheduledJobService
from app.core.db.db_postgres import SessionLocal
from app.workers.celery_app import celery_app


@celery_app.task(
    name="scheduled_jobs.tick",
    acks_late=False,
    max_retries=0,
)
def tick_scheduled_jobs():
    """Revisa tareas programadas vencidas y crea sus jobs reales."""
    with SessionLocal() as db:
        return ScheduledJobService(db).run_due()
