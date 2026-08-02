from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload

from app.api.jobs.constants import JobBatchStatus, JobItemStatus, JobStatus
from app.api.jobs.service import JobService
from app.models.analytics import AnalyticsIngestionItem, AnalyticsIngestionRun
from app.models.jobs import Job, JobBatch, JobItem
from app.services.data_lake import DataLakePathBuilder, ParquetDataLakeWriter
from app.services.ingestion.catalog import (
    MasterStorageMode,
    TableKind,
    get_icg_table_config,
)
from app.services.ingestion.extractor import IcgExtractor


class AnalyticsIngestionProcessor:
    def __init__(self, db_local, db_icg):
        self.db_local = db_local
        self.db_icg = db_icg
        self.paths = DataLakePathBuilder.from_settings()
        self.writer = ParquetDataLakeWriter()

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
        self._mark_run_running(batch.job.parameters.get("ingestion_run_id"), now)
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
        self._refresh_batch_runs(batch)
        return {"status": batch.status}

    def mark_failed(self, batch_id: UUID, error: str) -> None:
        batch = (
            self.db_local.query(JobBatch)
            .options(selectinload(JobBatch.items), selectinload(JobBatch.job))
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
                self._mark_ingestion_item(item, "FAILED", error=error, finished_at=now)
        batch.status = JobBatchStatus.FAILED.value
        batch.error_summary = error
        batch.finished_at = now
        self.db_local.commit()
        JobService(self.db_local).refresh_progress(batch.job_id)
        self._refresh_batch_runs(batch)

    def _process_item(self, batch: JobBatch, item: JobItem) -> None:
        payload = item.result_data or {}
        now = datetime.now(timezone.utc)
        item.status = JobItemStatus.RUNNING.value
        item.attempts += 1
        item.started_at = now
        batch.heartbeat_at = now
        self._mark_ingestion_item(item, "RUNNING", started_at=now)
        self.db_local.commit()

        try:
            result = self._execute_payload(payload)
            result["ingestion_run_id"] = payload.get("ingestion_run_id")
            item.status = JobItemStatus.SUCCEEDED.value
            item.external_status_code = 200
            item.result_data = result
            item.safe_error = None
            self._mark_ingestion_item(
                item,
                "SUCCEEDED",
                rows_count=result["rows_count"],
                output_path=result["output_path"],
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            self.db_local.rollback()
            item.status = JobItemStatus.FAILED.value
            item.safe_error = str(exc)[:2000]
            self._mark_ingestion_item(
                item,
                "FAILED",
                error=item.safe_error,
                finished_at=datetime.now(timezone.utc),
            )

        item.finished_at = datetime.now(timezone.utc)
        self._increment_progress(
            batch,
            succeeded=item.status == JobItemStatus.SUCCEEDED.value,
            failed=item.status == JobItemStatus.FAILED.value,
        )
        self.db_local.commit()

    def _execute_payload(self, payload: dict) -> dict:
        if payload["source"] != "icg":
            raise ValueError("Fuente no soportada")

        table_config = get_icg_table_config(payload["table_name"])
        extractor = IcgExtractor(self.db_icg)
        table_kind = TableKind(payload["table_kind"])

        if table_kind == TableKind.TRANSACTIONAL:
            business_date = date.fromisoformat(payload["business_date"])
            frame = extractor.extract(table_config, business_date=business_date)
            partition = self.paths.transactional_partition(
                source="icg",
                table_name=table_config.name,
                business_date=business_date,
            )
        else:
            frame = extractor.extract(table_config)
            storage_mode = MasterStorageMode(payload["master_storage_mode"])
            if storage_mode == MasterStorageMode.SNAPSHOT:
                partition = self.paths.master_snapshot(
                    source="icg",
                    table_name=table_config.name,
                    snapshot_date=date.today(),
                )
            else:
                partition = self.paths.master_latest(
                    source="icg",
                    table_name=table_config.name,
                )

        result = self.writer.write_partition(frame, partition, replace=True)
        return {
            "output_path": result.output_path,
            "rows_count": result.rows_count,
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

    def _mark_run_running(self, run_id: str | None, now: datetime) -> None:
        if not run_id:
            return
        (
            self.db_local.query(AnalyticsIngestionRun)
            .filter(AnalyticsIngestionRun.id == UUID(run_id))
            .update(
                {
                    AnalyticsIngestionRun.status: "RUNNING",
                    AnalyticsIngestionRun.started_at: func.coalesce(
                        AnalyticsIngestionRun.started_at,
                        now,
                    ),
                },
                synchronize_session=False,
            )
        )

    def _mark_ingestion_item(
        self,
        item: JobItem,
        status: str,
        *,
        rows_count: int | None = None,
        output_path: str | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        payload = item.result_data or {}
        run_id = payload.get("ingestion_run_id")
        if not run_id:
            return
        values = {AnalyticsIngestionItem.status: status}
        if rows_count is not None:
            values[AnalyticsIngestionItem.rows_count] = rows_count
        if output_path is not None:
            values[AnalyticsIngestionItem.output_path] = output_path
        if error is not None:
            values[AnalyticsIngestionItem.error] = error
        if started_at is not None:
            values[AnalyticsIngestionItem.started_at] = started_at
        if finished_at is not None:
            values[AnalyticsIngestionItem.finished_at] = finished_at

        (
            self.db_local.query(AnalyticsIngestionItem)
            .filter(
                AnalyticsIngestionItem.run_id == UUID(run_id),
                AnalyticsIngestionItem.reference == item.reference,
            )
            .update(values, synchronize_session=False)
        )

    def _refresh_run(self, run_id: str | None) -> None:
        if not run_id:
            return
        run = (
            self.db_local.query(AnalyticsIngestionRun)
            .options(selectinload(AnalyticsIngestionRun.items))
            .filter(AnalyticsIngestionRun.id == UUID(run_id))
            .first()
        )
        if not run:
            return
        statuses = [item.status for item in run.items]
        run.rows_count = sum(item.rows_count for item in run.items)
        output_paths = [item.output_path for item in run.items if item.output_path]
        run.output_path = "\n".join(output_paths) if output_paths else None
        if statuses and all(status in {"SUCCEEDED", "FAILED", "CANCELLED"} for status in statuses):
            run.finished_at = datetime.now(timezone.utc)
            if "FAILED" in statuses and "SUCCEEDED" in statuses:
                run.status = "COMPLETED_WITH_ERRORS"
            elif "FAILED" in statuses:
                run.status = "FAILED"
            elif "CANCELLED" in statuses:
                run.status = "CANCELLED"
            else:
                run.status = "COMPLETED"
        self.db_local.commit()

    def _refresh_batch_runs(self, batch: JobBatch) -> None:
        run_ids = {
            (item.result_data or {}).get("ingestion_run_id")
            for item in batch.items
            if isinstance(item.result_data, dict)
        }
        for run_id in run_ids:
            self._refresh_run(run_id)

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
                self._mark_ingestion_item(item, "CANCELLED", finished_at=now)
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
