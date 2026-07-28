from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload

from app.api.finance.libro_mayor.libro_mayor_service import LibroMayorService
from app.api.finance.libro_mayor.service.libro_mayor_reproces_service import (
    LibroMayorReprocessService,
)
from app.api.jobs.constants import JobBatchStatus, JobItemStatus, JobStatus
from app.api.jobs.service import JobService
from app.models.jobs import Job, JobBatch, JobItem


class LibroMayorJobProcessor:
    """Procesa jobs de libro mayor guardando avance por item."""

    def __init__(self, db_local, db_sap=None):
        self.db_local = db_local
        self.db_sap = db_sap

    def process(self, batch_id: UUID, task_id: str) -> dict:
        batch = (
            self.db_local.query(JobBatch)
            .options(selectinload(JobBatch.job), selectinload(JobBatch.items))
            .filter(JobBatch.id == batch_id)
            .first()
        )
        if not batch:
            return {"status": "not_found"}
        if batch.celery_task_id != task_id:
            return {"status": "stale_task"}
        if batch.status in {
            JobBatchStatus.COMPLETED.value,
            JobBatchStatus.COMPLETED_WITH_ERRORS.value,
            JobBatchStatus.FAILED.value,
            JobBatchStatus.CANCELLED.value,
        }:
            return {"status": batch.status}

        if self._is_cancel_requested(batch.job):
            self._cancel_pending(batch)
            return {"status": JobBatchStatus.CANCELLED.value}

        now = datetime.now(timezone.utc)
        claimed = (
            self.db_local.query(JobBatch)
            .filter(
                JobBatch.id == batch.id,
                JobBatch.celery_task_id == task_id,
                JobBatch.status.in_(
                    [
                        JobBatchStatus.PENDING.value,
                        JobBatchStatus.QUEUED.value,
                        JobBatchStatus.RUNNING.value,
                        JobBatchStatus.RETRYING.value,
                    ]
                ),
            )
            .update(
                {
                    JobBatch.status: JobBatchStatus.RUNNING.value,
                    JobBatch.attempts: JobBatch.attempts + 1,
                    JobBatch.started_at: func.coalesce(JobBatch.started_at, now),
                    JobBatch.heartbeat_at: now,
                },
                synchronize_session=False,
            )
        )
        if not claimed:
            self.db_local.rollback()
            return {"status": "not_claimed"}

        (
            self.db_local.query(Job)
            .filter(
                Job.id == batch.job_id,
                Job.status.notin_(
                    [JobStatus.CANCEL_REQUESTED.value, JobStatus.CANCELLED.value]
                ),
            )
            .update(
                {
                    Job.status: case(
                        (
                            Job.status == JobStatus.DISPATCH_FAILED.value,
                            JobStatus.DISPATCH_FAILED.value,
                        ),
                        else_=JobStatus.RUNNING.value,
                    ),
                    Job.started_at: func.coalesce(Job.started_at, now),
                },
                synchronize_session=False,
            )
        )
        self.db_local.commit()
        self.db_local.refresh(batch)
        self.db_local.refresh(batch.job)

        for item in batch.items:
            if item.status != JobItemStatus.PENDING.value:
                continue
            self.db_local.refresh(batch.job, attribute_names=["status"])
            if self._is_cancel_requested(batch.job):
                break
            self._process_item(batch, item)

        if self._is_cancel_requested(batch.job):
            self._cancel_pending(batch)
        else:
            self._finish_batch(batch)
        return {"status": batch.status}

    def mark_failed(self, batch_id: UUID, error: str) -> None:
        batch = (
            self.db_local.query(JobBatch)
            .options(selectinload(JobBatch.items))
            .filter(JobBatch.id == batch_id)
            .first()
        )
        if not batch:
            return
        now = datetime.now(timezone.utc)
        for item in batch.items:
            if item.status in {JobItemStatus.PENDING.value, JobItemStatus.RUNNING.value}:
                item.status = JobItemStatus.FAILED.value
                item.safe_error = error
                item.finished_at = now
        batch.status = JobBatchStatus.FAILED.value
        batch.error_summary = error
        batch.finished_at = now
        self.db_local.commit()
        JobService(self.db_local).refresh_progress(batch.job_id)

    def _process_item(self, batch: JobBatch, item: JobItem) -> None:
        payload = item.result_data or {}
        item.status = JobItemStatus.RUNNING.value
        item.attempts += 1
        item.started_at = datetime.now(timezone.utc)
        batch.heartbeat_at = item.started_at
        self.db_local.commit()

        try:
            result = self._execute_payload(payload)
            item.status = JobItemStatus.SUCCEEDED.value
            item.external_status_code = 200
            item.result_data = result
            item.safe_error = None
        except Exception as exc:
            self.db_local.rollback()
            item.status = JobItemStatus.FAILED.value
            item.safe_error = str(exc)[:2000]

        item.finished_at = datetime.now(timezone.utc)
        self._increment_progress(
            batch,
            succeeded=item.status == JobItemStatus.SUCCEEDED.value,
            failed=item.status == JobItemStatus.FAILED.value,
        )
        self.db_local.commit()

    def _execute_payload(self, payload: dict) -> dict:
        operation = payload["operation"]
        account = payload["account"]
        start_date = datetime.fromisoformat(payload["start_date"]).date()
        end_date = datetime.fromisoformat(payload["end_date"]).date()

        if operation == "sync":
            if self.db_sap is None:
                raise ValueError("La sesion SAP es obligatoria para sincronizar")
            return LibroMayorService(self.db_local, self.db_sap).sync(
                start_date=start_date,
                end_date=end_date,
                account=account,
            )

        if operation == "sync_delta":
            if self.db_sap is None:
                raise ValueError("La sesion SAP es obligatoria para delta")
            return LibroMayorService(self.db_local, self.db_sap).sync_delta(
                start_date=start_date,
                end_date=end_date,
                account=account,
            )

        if operation == "reprocess":
            return LibroMayorReprocessService(self.db_local).reprocess_date_range(
                account=account,
                start_date=start_date,
                end_date=end_date,
            )

        raise ValueError(f"Operacion de libro mayor no soportada: {operation}")

    def _finish_batch(self, batch: JobBatch) -> None:
        self.db_local.refresh(batch, attribute_names=["items"])
        self._set_batch_counts(batch)
        batch.status = (
            JobBatchStatus.COMPLETED_WITH_ERRORS.value
            if batch.failed_items
            else JobBatchStatus.COMPLETED.value
        )
        batch.finished_at = datetime.now(timezone.utc)
        batch.heartbeat_at = batch.finished_at
        self.db_local.commit()
        JobService(self.db_local).refresh_progress(batch.job_id)

    def _cancel_pending(self, batch: JobBatch) -> None:
        now = datetime.now(timezone.utc)
        for item in batch.items:
            if item.status == JobItemStatus.PENDING.value:
                item.status = JobItemStatus.CANCELLED.value
                item.finished_at = now
        batch.status = JobBatchStatus.CANCELLED.value
        batch.finished_at = now
        self._set_batch_counts(batch)
        self.db_local.commit()
        JobService(self.db_local).refresh_progress(batch.job_id)

    def _increment_progress(
        self,
        batch: JobBatch,
        *,
        succeeded: bool,
        failed: bool,
    ) -> None:
        values = {Job.processed_items: Job.processed_items + 1}
        if succeeded:
            values[Job.succeeded_items] = Job.succeeded_items + 1
            batch.succeeded_items += 1
        if failed:
            values[Job.failed_items] = Job.failed_items + 1
            batch.failed_items += 1
        (
            self.db_local.query(Job)
            .filter(Job.id == batch.job_id)
            .update(values, synchronize_session=False)
        )

    @staticmethod
    def _set_batch_counts(batch: JobBatch) -> None:
        statuses = [item.status for item in batch.items]
        batch.succeeded_items = statuses.count(JobItemStatus.SUCCEEDED.value)
        batch.failed_items = statuses.count(JobItemStatus.FAILED.value)
        batch.cancelled_items = statuses.count(JobItemStatus.CANCELLED.value)

    @staticmethod
    def _is_cancel_requested(job: Job) -> bool:
        return job.status in {
            JobStatus.CANCEL_REQUESTED.value,
            JobStatus.CANCELLED.value,
        }
