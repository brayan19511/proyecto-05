from uuid import UUID, uuid4

from app.api.jobs.constants import JobBatchStatus, JobType
from app.api.jobs.repository import JobRepository
from app.api.sap.handlers import get_sap_item_handler
from app.core.db.db_postgres import SessionLocal
from app.workers.email_tasks import process_payment_provider_email_batch
from app.workers.sap_tasks import process_sap_batch


JOB_TASKS = {
    JobType.SAP_DOCUMENT_ACTION.value: (process_sap_batch, "sap"),
    JobType.SAP_RECONCILIATION.value: (process_sap_batch, "sap"),
    JobType.PAYMENT_PROVIDER_EMAIL.value: (
        process_payment_provider_email_batch,
        "email",
    ),
}


def dispatch_job(job_id: UUID) -> None:
    """Publica en RabbitMQ los lotes pendientes de un job."""
    with SessionLocal() as db:
        repository = JobRepository(db)
        job = repository.get_by_id(job_id)
        if not job:
            raise ValueError("Tarea no encontrada")

        task_config = JOB_TASKS.get(job.job_type)
        if not task_config:
            raise ValueError(f"Tipo de tarea no soportado: {job.job_type}")
        task, queue = task_config
        if queue == "sap":
            # SAP mantiene validacion adicional por handler de negocio.
            get_sap_item_handler(job.job_type)

        for batch in repository.get_dispatchable_batches(job_id):
            task_id = str(uuid4())
            # Guardamos primero el task_id. Si llega un mensaje viejo despues
            # de un reintento, el worker lo detecta y no procesa dos veces.
            batch.celery_task_id = task_id
            batch.status = JobBatchStatus.QUEUED.value
            db.commit()
            try:
                task.apply_async(
                    args=[str(batch.id)],
                    task_id=task_id,
                    queue=queue,
                )
            except Exception:
                # Si RabbitMQ falla justo aqui, dejamos este lote pendiente
                # para que se pueda volver a publicar luego.
                batch.celery_task_id = None
                batch.status = JobBatchStatus.PENDING.value
                db.commit()
                raise
