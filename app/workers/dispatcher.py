from uuid import UUID, uuid4

from app.api.jobs.constants import JobBatchStatus
from app.api.jobs.repository import JobRepository
from app.api.sap.handlers import get_sap_item_handler
from app.core.db.db_postgres import SessionLocal
from app.workers.sap_tasks import process_sap_batch


def dispatch_job(job_id: UUID) -> None:
    """Publica en RabbitMQ los lotes pendientes de un job."""
    with SessionLocal() as db:
        repository = JobRepository(db)
        job = repository.get_by_id(job_id)
        if not job:
            raise ValueError("Tarea no encontrada")

        # Si existe handler para el job_type, este dispatcher puede publicarlo.
        get_sap_item_handler(job.job_type)

        for batch in repository.get_dispatchable_batches(job_id):
            task_id = str(uuid4())
            # Guardamos primero el task_id. Si llega un mensaje viejo despues
            # de un reintento, el worker lo detecta y no procesa dos veces.
            batch.celery_task_id = task_id
            batch.status = JobBatchStatus.QUEUED.value
            db.commit()
            try:
                process_sap_batch.apply_async(
                    args=[str(batch.id)],
                    task_id=task_id,
                    queue="sap",
                )
            except Exception:
                # Si RabbitMQ falla justo aqui, dejamos este lote pendiente
                # para que se pueda volver a publicar luego.
                batch.celery_task_id = None
                batch.status = JobBatchStatus.PENDING.value
                db.commit()
                raise
