from uuid import UUID, uuid4

from app.api.jobs.constants import JobBatchStatus, JobType
from app.api.jobs.repository import JobRepository
from app.core.db.db_postgres import SessionLocal
from app.workers.celery_app import celery_app


TASK_BY_JOB_TYPE = {
    JobType.SAP_DOCUMENT_ACTION.value: "jobs.sap.process_batch",
}


def dispatch_job(job_id: UUID) -> None:
    """Publish undispatched batches using small, non-sensitive messages."""
    with SessionLocal() as db:
        repository = JobRepository(db)
        job = repository.get_by_id(job_id)
        task_name = TASK_BY_JOB_TYPE.get(job.job_type if job else "")
        if not job or not task_name:
            raise ValueError("Tipo de tarea no soportado")

        for batch in repository.get_dispatchable_batches(job_id):
            task_id = str(uuid4())
            # Persist the id first so a stale message can be rejected safely.
            batch.celery_task_id = task_id
            batch.status = JobBatchStatus.QUEUED.value
            db.commit()
            try:
                celery_app.send_task(
                    task_name,
                    args=[str(batch.id)],
                    task_id=task_id,
                    queue="sap",
                )
            except Exception:
                # Previously published batches keep their ids; only this one
                # becomes eligible for a later dispatch retry.
                batch.celery_task_id = None
                batch.status = JobBatchStatus.PENDING.value
                db.commit()
                raise
