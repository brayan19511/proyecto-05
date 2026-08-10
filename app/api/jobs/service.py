from collections.abc import Callable, Iterable
from datetime import datetime, timezone
import logging
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.jobs.constants import (
    JobBatchStatus,
    JobItemStatus,
    JobStatus,
    JobTriggerSource,
    TERMINAL_JOB_STATUSES,
)
from app.api.jobs.repository import JobRepository
from app.api.jobs.schemas import JobItemPageResponse, JobPageResponse
from app.core.exceptions import ConflictError, NotFoundError
from app.models.jobs import Job, JobBatch, JobItem


JobDispatcher = Callable[[UUID], None]
logger = logging.getLogger(__name__)


def chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


class JobService:
    def __init__(
        self,
        db: Session,
        dispatcher: JobDispatcher | None = None,
    ):
        self.db = db
        self.repository = JobRepository(db)
        self.dispatcher = dispatcher

    def create_job(
        self,
        *,
        job_type: str,
        parameters: dict,
        references: list[int | str],
        user_id: UUID,
        batch_size: int,
        idempotency_key: str | None = None,
        parent_job_id: UUID | None = None,
        scheduled_job_id: UUID | None = None,
        trigger_source: str = JobTriggerSource.API.value,
        encrypted_secrets: str | None = None,
        item_payloads: dict[str, dict | list | str] | None = None,
    ) -> Job:
        normalized = list(dict.fromkeys(str(item) for item in references))
        if not normalized:
            raise ConflictError("La tarea debe contener al menos un elemento")
        if batch_size <= 0:
            raise ConflictError("El tamano del lote debe ser mayor que cero")

        # Double clicks or HTTP retries return the same functional operation.
        # The unique constraint also protects this rule under concurrency.
        if idempotency_key:
            existing = self.repository.get_by_idempotency_key(
                user_id=user_id,
                job_type=job_type,
                idempotency_key=idempotency_key,
            )
            if existing:
                return self.get_job(
                    existing.id,
                    user_id=user_id,
                    can_view_all=False,
                )

        job = Job(
            id=uuid4(),
            parent_job_id=parent_job_id,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
            job_type=job_type,
            status=JobStatus.CREATED.value,
            parameters=parameters,
            idempotency_key=idempotency_key,
            encrypted_secrets=encrypted_secrets,
            total_items=len(normalized),
            created_by=user_id,
        )

        for sequence, references_chunk in enumerate(
            chunked(normalized, batch_size),
            start=1,
        ):
            batch = JobBatch(
                sequence=sequence,
                status=JobBatchStatus.PENDING.value,
                total_items=len(references_chunk),
            )
            batch.items = []
            for reference in references_chunk:
                item = JobItem(
                    job_id=job.id,
                    reference=reference,
                    status=JobItemStatus.PENDING.value,
                )
                # Algunas tareas necesitan guardar el payload ya normalizado
                # por item. El worker lo lee desde aqui y no vuelve a tocar
                # archivos subidos por el usuario.
                if item_payloads:
                    item.result_data = item_payloads.get(reference)
                batch.items.append(item)
            job.batches.append(batch)

        # Avisamos al worker solo despues de guardar job, lotes e items.
        job.total_batches = len(job.batches)
        job.status = JobStatus.QUEUED.value
        self.db.add(job)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if idempotency_key:
                existing = self.repository.get_by_idempotency_key(
                    user_id=user_id,
                    job_type=job_type,
                    idempotency_key=idempotency_key,
                )
                if existing:
                    return self.get_job(
                        existing.id,
                        user_id=user_id,
                        can_view_all=False,
                    )
            raise

        self._dispatch(job)
        return self.get_job(job.id, user_id=user_id, can_view_all=False)

    def list_jobs(
        self,
        *,
        current_user_id: UUID,
        can_view_all: bool,
        mine: bool,
        job_type: str | None,
        status: str | None,
        scheduled_job_id: UUID | None,
        limit: int,
        offset: int,
    ) -> JobPageResponse:
        user_filter = current_user_id if mine or not can_view_all else None
        items, total = self.repository.list_jobs(
            user_id=user_filter,
            job_type=job_type,
            status=status,
            scheduled_job_id=scheduled_job_id,
            limit=limit,
            offset=offset,
        )
        return JobPageResponse.build(items, total, limit, offset)

    def get_job(
        self,
        job_id: UUID,
        *,
        user_id: UUID,
        can_view_all: bool,
        with_items: bool = False,
    ) -> Job:
        job = self.repository.get_by_id(
            job_id,
            with_batches=True,
            with_items=with_items,
        )
        if not job:
            raise NotFoundError("Tarea no encontrada")
        self._ensure_access(job, user_id, can_view_all)
        return job

    def list_items(
        self,
        job_id: UUID,
        *,
        user_id: UUID,
        can_view_all: bool,
        status: str | None,
        limit: int,
        offset: int,
    ) -> JobItemPageResponse:
        self.get_job(job_id, user_id=user_id, can_view_all=can_view_all)
        items, total = self.repository.list_items(
            job_id=job_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return JobItemPageResponse.build(items, total, limit, offset)

    def cancel_job(
        self,
        job_id: UUID,
        *,
        user_id: UUID,
        can_cancel_all: bool,
    ) -> Job:
        job = self.get_job(
            job_id,
            user_id=user_id,
            can_view_all=can_cancel_all,
            with_items=True,
        )
        if JobStatus(job.status) in TERMINAL_JOB_STATUSES:
            raise ConflictError("La tarea ya se encuentra finalizada")

        now = datetime.now(timezone.utc)
        job.status = JobStatus.CANCEL_REQUESTED.value
        job.cancel_requested_at = now
        job.updated_by = user_id

        task_ids = []
        for batch in job.batches:
            if batch.celery_task_id:
                task_ids.append(batch.celery_task_id)
            if batch.status in {
                JobBatchStatus.PENDING.value,
                JobBatchStatus.QUEUED.value,
                JobBatchStatus.RETRYING.value,
            }:
                batch.status = JobBatchStatus.CANCELLED.value
                batch.finished_at = now
                for item in batch.items:
                    if item.status == JobItemStatus.PENDING.value:
                        item.status = JobItemStatus.CANCELLED.value
                        item.finished_at = now
                statuses = [item.status for item in batch.items]
                batch.succeeded_items = statuses.count(
                    JobItemStatus.SUCCEEDED.value
                )
                batch.failed_items = statuses.count(
                    JobItemStatus.FAILED.value
                )
                batch.cancelled_items = statuses.count(
                    JobItemStatus.CANCELLED.value
                )

        self.db.commit()
        self.refresh_progress(job.id)
        self._revoke_tasks(task_ids)
        return self.get_job(job.id, user_id=user_id, can_view_all=True)

    def retry_job(
        self,
        job_id: UUID,
        *,
        user_id: UUID,
        can_retry_all: bool,
        batch_size: int,
    ) -> Job:
        job = self.get_job(
            job_id,
            user_id=user_id,
            can_view_all=can_retry_all,
        )
        dispatchable_batches = self.repository.get_dispatchable_batches(job.id)
        if (
            dispatchable_batches
            and JobStatus(job.status) not in TERMINAL_JOB_STATUSES
        ):
            job.error_summary = None
            job.status = JobStatus.QUEUED.value
            self.db.commit()
            self._dispatch(job)
            return self.get_job(job.id, user_id=user_id, can_view_all=True)

        # Reintentar fallidos crea una tarea hija. La ejecucion original queda
        # como historial para auditoria y para la UX.
        references = self.repository.get_failed_references(job.id)
        if not references:
            raise ConflictError("La tarea no tiene elementos fallidos para reintentar")
        item_payloads = self.repository.get_failed_item_payloads(job.id)

        return self.create_job(
            job_type=job.job_type,
            parameters=job.parameters,
            references=references,
            user_id=user_id,
            batch_size=batch_size,
            parent_job_id=job.id,
            scheduled_job_id=job.scheduled_job_id,
            trigger_source=JobTriggerSource.RETRY.value,
            encrypted_secrets=job.encrypted_secrets,
            item_payloads=item_payloads or None,
        )

    def refresh_progress(self, job_id: UUID) -> None:
        job = self.repository.get_by_id(job_id)
        if not job:
            return

        # Agregamos en PostgreSQL. Asi una tarea grande no carga todos los
        # items en memoria solo para actualizar contadores.
        status_counts = dict(
            self.db.query(JobItem.status, func.count(JobItem.id))
            .filter(JobItem.job_id == job_id)
            .group_by(JobItem.status)
            .all()
        )
        job.succeeded_items = status_counts.get(
            JobItemStatus.SUCCEEDED.value,
            0,
        )
        job.failed_items = status_counts.get(JobItemStatus.FAILED.value, 0)
        job.cancelled_items = status_counts.get(
            JobItemStatus.CANCELLED.value,
            0,
        )
        job.processed_items = (
            job.succeeded_items + job.failed_items + job.cancelled_items
        )
        job.finished_batches = (
            self.db.query(func.count(JobBatch.id))
            .filter(
                JobBatch.job_id == job_id,
                JobBatch.status.in_(
                    [
                        JobBatchStatus.COMPLETED.value,
                        JobBatchStatus.COMPLETED_WITH_ERRORS.value,
                        JobBatchStatus.FAILED.value,
                        JobBatchStatus.CANCELLED.value,
                    ]
                ),
            )
            .scalar()
            or 0
        )

        if job.finished_batches == job.total_batches:
            job.finished_at = datetime.now(timezone.utc)
            if job.cancel_requested_at:
                job.status = JobStatus.CANCELLED.value
            elif job.failed_items and job.succeeded_items:
                job.status = JobStatus.COMPLETED_WITH_ERRORS.value
            elif job.failed_items:
                job.status = JobStatus.FAILED.value
            else:
                job.status = JobStatus.COMPLETED.value
        self.db.commit()

    def _dispatch(self, job: Job) -> None:
        if not self.dispatcher:
            return
        try:
            self.dispatcher(job.id)
        except Exception:
            logger.exception("Could not dispatch job id=%s", job.id)
            current = self.repository.get_by_id(job.id)
            current.status = JobStatus.DISPATCH_FAILED.value
            current.error_summary = "No se pudo publicar la tarea en la cola"
            self.db.commit()

    @staticmethod
    def _ensure_access(job: Job, user_id: UUID, can_view_all: bool) -> None:
        if not can_view_all and job.created_by != user_id:
            raise NotFoundError("Tarea no encontrada")

    @staticmethod
    def _revoke_tasks(task_ids: list[str]) -> None:
        if not task_ids:
            return
        try:
            from app.workers.celery_app import celery_app

            celery_app.control.revoke(task_ids, terminate=False)
        except Exception:
            # La cancelacion cooperativa sigue funcionando por job.status.
            logger.warning(
                "Could not revoke Celery tasks; cancellation remains cooperative",
                exc_info=True,
            )
            return
