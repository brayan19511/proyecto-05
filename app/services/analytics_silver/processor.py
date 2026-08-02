from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload

from app.api.jobs.constants import JobBatchStatus, JobItemStatus, JobStatus
from app.api.jobs.service import JobService
from app.models.jobs import Job, JobBatch, JobItem
from app.services.analytics_silver import IcgSilverSalesBuilder


class AnalyticsSilverJobProcessor:
    def __init__(self, db_local):
        self.db_local = db_local

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

        self._mark_job_running(batch.job_id, now)
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
        now = datetime.now(timezone.utc)
        item.status = JobItemStatus.RUNNING.value
        item.attempts += 1
        item.started_at = now
        batch.heartbeat_at = now
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
        if payload.get("source") != "icg":
            raise ValueError("Fuente silver no soportada")
        if payload.get("dataset_group") != "sales":
            raise ValueError("Grupo silver no soportado")

        business_date = date.fromisoformat(payload["business_date"])
        results = IcgSilverSalesBuilder().build_day(business_date=business_date)
        return {
            "business_date": business_date.isoformat(),
            "items": [
                {
                    "dataset_name": item.dataset_name,
                    "business_date": item.business_date.isoformat(),
                    "output_path": item.output_path,
                    "rows_count": item.rows_count,
                }
                for item in results
            ],
        }

    def _mark_job_running(self, job_id: UUID, now: datetime) -> None:
        (
            self.db_local.query(Job)
            .filter(
                Job.id == job_id,
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
