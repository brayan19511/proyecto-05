from datetime import datetime, timezone
import json
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload

from app.api.jobs.constants import (
    JobBatchStatus,
    JobItemStatus,
    JobStatus,
)
from app.api.jobs.service import JobService
from app.api.sap.handlers import get_sap_item_handler
from app.api.sap.handlers.base import SapItemHandler
from app.api.sap.service.sap_document_service import SapDocumentService
from app.core.exceptions import (
    SAPAuthenticationError,
    SAPConnectionError,
    SAPRequestError,
)
from app.core.secret_cipher import decrypt_job_secrets
from app.models.jobs import Job, JobBatch, JobItem
from app.models.sap.sap_models import SAPCredentials


def safe_sap_error(detail, max_length: int = 2000) -> str:
    if isinstance(detail, dict):
        error = detail.get("error", detail)
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else error
        if isinstance(message, dict):
            message = message.get("value") or message.get("message")
        value = f"{code}: {message}" if code and message else str(message or code)
    elif isinstance(detail, list):
        value = json.dumps(detail[:5], ensure_ascii=True)
    else:
        value = str(detail)
    return value[:max_length]


class SapJobProcessor:
    def __init__(self, db):
        self.db = db

    def process(self, batch_id: UUID, task_id: str) -> dict:
        batch = (
            self.db.query(JobBatch)
            .options(
                selectinload(JobBatch.job),
                selectinload(JobBatch.items),
            )
            .filter(JobBatch.id == batch_id)
            .first()
        )
        if not batch:
            return {"status": "not_found"}
        if batch.celery_task_id != task_id:
            # A previous publish can arrive after the batch was redispatched.
            return {"status": "stale_task"}
        if batch.status in {
            JobBatchStatus.COMPLETED.value,
            JobBatchStatus.COMPLETED_WITH_ERRORS.value,
            JobBatchStatus.FAILED.value,
            JobBatchStatus.CANCELLED.value,
        }:
            return {"status": batch.status}

        # Si el worker se apago con items RUNNING, no los repetimos a ciegas:
        # una accion SAP podria no ser idempotente y ejecutarse dos veces.
        self._mark_uncertain_items(batch)
        if self._is_cancel_requested(batch.job):
            self._cancel_pending(batch)
            return {"status": JobBatchStatus.CANCELLED.value}

        now = datetime.now(timezone.utc)
        # Este update condicional evita que una cancelacion y el inicio del
        # worker se pisen si ocurren al mismo tiempo.
        claimed = (
            self.db.query(JobBatch)
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
                    JobBatch.started_at: func.coalesce(
                        JobBatch.started_at,
                        now,
                    ),
                    JobBatch.heartbeat_at: now,
                },
                synchronize_session=False,
            )
        )
        if not claimed:
            self.db.rollback()
            return {"status": "not_claimed"}

        job_started = (
            self.db.query(Job)
            .filter(
                Job.id == batch.job_id,
                Job.status.notin_(
                    [
                        JobStatus.CANCEL_REQUESTED.value,
                        JobStatus.CANCELLED.value,
                    ]
                ),
            )
            .update(
                {
                    # Si fallo publicar algun lote, mantenemos visible ese
                    # estado aunque los lotes ya publicados sigan avanzando.
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
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(batch.job)
        if not job_started or self._is_cancel_requested(batch.job):
            self._cancel_pending(batch)
            return {"status": JobBatchStatus.CANCELLED.value}

        parameters = batch.job.parameters
        credentials = decrypt_job_secrets(batch.job.encrypted_secrets)
        document_service = SapDocumentService(
            SAPCredentials(
                company=parameters["database"],
                user_name=credentials["user"],
                password=credentials["password"],
            )
        )

        try:
            with document_service.build_client() as client:
                handler_class = get_sap_item_handler(batch.job.job_type)
                handler = handler_class(document_service, client)
                for item in batch.items:
                    if item.status != JobItemStatus.PENDING.value:
                        continue
                    self.db.refresh(batch.job, attribute_names=["status"])
                    if self._is_cancel_requested(batch.job):
                        break
                    self._process_item(
                        batch,
                        item,
                        handler,
                    )
        except SAPConnectionError:
            self.db.rollback()
            raise
        except SAPAuthenticationError as exc:
            self._fail_pending(batch, safe_sap_error(exc))

        if self._is_cancel_requested(batch.job):
            self._cancel_pending(batch)
        else:
            self._finish_batch(batch)
        return {"status": batch.status}

    def mark_retrying(self, batch_id: UUID, error: str) -> None:
        batch = self.db.get(JobBatch, batch_id)
        if not batch:
            return
        for item in batch.items:
            if item.status == JobItemStatus.RUNNING.value:
                item.status = JobItemStatus.PENDING.value
                item.safe_error = None
                item.started_at = None
        batch.status = JobBatchStatus.RETRYING.value
        batch.error_summary = error
        batch.heartbeat_at = datetime.now(timezone.utc)
        self.db.commit()

    def mark_failed(self, batch_id: UUID, error: str) -> None:
        batch = (
            self.db.query(JobBatch)
            .options(selectinload(JobBatch.items))
            .filter(JobBatch.id == batch_id)
            .first()
        )
        if not batch:
            return
        if batch.status in {
            JobBatchStatus.COMPLETED.value,
            JobBatchStatus.COMPLETED_WITH_ERRORS.value,
            JobBatchStatus.CANCELLED.value,
        }:
            return
        self._fail_pending(batch, error)
        batch.status = JobBatchStatus.FAILED.value
        batch.error_summary = error
        batch.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        JobService(self.db).refresh_progress(batch.job_id)

    def _process_item(
        self,
        batch: JobBatch,
        item: JobItem,
        handler: SapItemHandler,
    ) -> None:
        item.status = JobItemStatus.RUNNING.value
        item.attempts += 1
        item.started_at = datetime.now(timezone.utc)
        batch.heartbeat_at = item.started_at
        # Guardamos RUNNING antes de llamar a SAP. Si el worker cae, luego
        # sabremos que ese item quedo incierto y requiere revision.
        self.db.commit()

        try:
            handler.execute(batch, item)
            item.status = JobItemStatus.SUCCEEDED.value
            item.external_status_code = 200
            item.result_data = {"completed": True}
            item.safe_error = None
        except SAPRequestError as exc:
            item.status = JobItemStatus.FAILED.value
            item.external_status_code = exc.status_code
            item.safe_error = safe_sap_error(exc.detail)
        except SAPConnectionError:
            item.status = JobItemStatus.PENDING.value
            item.started_at = None
            self.db.commit()
            raise

        item.finished_at = datetime.now(timezone.utc)
        self._increment_progress(
            batch,
            succeeded=item.status == JobItemStatus.SUCCEEDED.value,
            failed=item.status == JobItemStatus.FAILED.value,
        )
        # Cada resultado externo se persiste de inmediato. Si el lote se
        # reintenta, los items terminales se saltan y no se repiten.
        self.db.commit()

    def _finish_batch(self, batch: JobBatch) -> None:
        self.db.refresh(batch, attribute_names=["items"])
        statuses = [item.status for item in batch.items]
        batch.succeeded_items = statuses.count(JobItemStatus.SUCCEEDED.value)
        batch.failed_items = statuses.count(JobItemStatus.FAILED.value)
        batch.cancelled_items = statuses.count(JobItemStatus.CANCELLED.value)
        batch.status = (
            JobBatchStatus.COMPLETED_WITH_ERRORS.value
            if batch.failed_items
            else JobBatchStatus.COMPLETED.value
        )
        batch.finished_at = datetime.now(timezone.utc)
        batch.heartbeat_at = batch.finished_at
        batch.error_summary = None
        self.db.commit()
        JobService(self.db).refresh_progress(batch.job_id)

    def _cancel_pending(self, batch: JobBatch) -> None:
        now = datetime.now(timezone.utc)
        for item in batch.items:
            if item.status == JobItemStatus.PENDING.value:
                item.status = JobItemStatus.CANCELLED.value
                item.finished_at = now
        batch.status = JobBatchStatus.CANCELLED.value
        batch.finished_at = now
        self._set_batch_counts(batch)
        self.db.commit()
        JobService(self.db).refresh_progress(batch.job_id)

    def _fail_pending(self, batch: JobBatch, error: str) -> None:
        now = datetime.now(timezone.utc)
        for item in batch.items:
            if item.status in {
                JobItemStatus.PENDING.value,
                JobItemStatus.RUNNING.value,
            }:
                item.status = JobItemStatus.FAILED.value
                item.safe_error = error
                item.finished_at = now
        self._set_batch_counts(batch)
        self.db.commit()

    def _mark_uncertain_items(self, batch: JobBatch) -> None:
        # RUNNING al reanudar significa "no se si SAP alcanzo a procesarlo".
        # Preferimos marcarlo fallido para revision manual antes que duplicarlo.
        uncertain = [
            item
            for item in batch.items
            if item.status == JobItemStatus.RUNNING.value
        ]
        if not uncertain:
            return
        now = datetime.now(timezone.utc)
        for item in uncertain:
            item.status = JobItemStatus.FAILED.value
            item.safe_error = (
                "Resultado incierto tras interrupcion; requiere revision"
            )
            item.finished_at = now
        self.db.commit()

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
            self.db.query(Job)
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
