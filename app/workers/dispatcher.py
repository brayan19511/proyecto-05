from uuid import UUID, uuid4

from app.api.jobs.constants import JobBatchStatus, JobType
from app.api.jobs.repository import JobRepository
from app.api.sap.handlers import get_sap_item_handler
from app.core.db.db_postgres import SessionLocal
from app.workers.analytics_tasks import process_analytics_batch
from app.workers.email_tasks import process_payment_provider_email_batch
from app.workers.ledger_tasks import process_ledger_batch
from app.workers.sap_tasks import process_sap_batch
from app.workers.silver_tasks import process_analytics_silver_batch


QUEUE_LIGHT = "light"
QUEUE_HEAVY = "heavy"
QUEUE_EMAIL = "email"
LEDGER_LIGHT_MAX_ITEMS = 1

JOB_TASKS = {
    JobType.SAP_DOCUMENT_ACTION.value: process_sap_batch,
    JobType.SAP_RECONCILIATION.value: process_sap_batch,
    JobType.PAYMENT_PROVIDER_EMAIL.value: process_payment_provider_email_batch,
    JobType.LEDGER_SYNC.value: process_ledger_batch,
    JobType.LEDGER_SYNC_DELTA.value: process_ledger_batch,
    JobType.LEDGER_REPROCESS.value: process_ledger_batch,
    JobType.ANALYTICS_EXTRACT.value: process_analytics_batch,
    JobType.ANALYTICS_SILVER_BUILD.value: process_analytics_silver_batch,
}


def resolve_job_queue(job) -> str:
    """Define la cola por perfil de carga, no por nombre del modulo."""
    if job.job_type == JobType.PAYMENT_PROVIDER_EMAIL.value:
        return QUEUE_EMAIL

    if job.job_type in {
        JobType.SAP_DOCUMENT_ACTION.value,
        JobType.SAP_RECONCILIATION.value,
        JobType.LEDGER_REPROCESS.value,
        JobType.ANALYTICS_EXTRACT.value,
        JobType.ANALYTICS_SILVER_BUILD.value,
    }:
        return QUEUE_HEAVY

    if job.job_type in {
        JobType.LEDGER_SYNC.value,
        JobType.LEDGER_SYNC_DELTA.value,
    }:
        # Un dia/cuenta es corto; rangos mas grandes van a heavy para no
        # quitar capacidad a tareas rapidas.
        if job.total_items <= LEDGER_LIGHT_MAX_ITEMS:
            return QUEUE_LIGHT
        return QUEUE_HEAVY

    return QUEUE_LIGHT


JOB_TYPES_WITH_SAP_HANDLER = {
    JobType.SAP_DOCUMENT_ACTION.value,
    JobType.SAP_RECONCILIATION.value,
}

def dispatch_job(job_id: UUID) -> None:
    """Publica en RabbitMQ los lotes pendientes de un job."""
    with SessionLocal() as db:
        repository = JobRepository(db)
        job = repository.get_by_id(job_id)
        if not job:
            raise ValueError("Tarea no encontrada")

        task = JOB_TASKS.get(job.job_type)
        if not task:
            raise ValueError(f"Tipo de tarea no soportado: {job.job_type}")
        queue = resolve_job_queue(job)
        if job.job_type in JOB_TYPES_WITH_SAP_HANDLER:
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
