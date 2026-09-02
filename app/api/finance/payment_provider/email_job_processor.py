from datetime import datetime, timezone
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload

from app.api.finance.payment_provider.archive_service import (
    PaymentProviderArchiveService,
)
from app.api.jobs.constants import JobBatchStatus, JobItemStatus, JobStatus
from app.api.jobs.service import JobService
from app.models.jobs import Job, JobBatch, JobItem
from app.services.email import EmailAttachment, EmailService


logger = logging.getLogger(__name__)


class PaymentProviderEmailJobProcessor:
    """Procesa correos de pagos a proveedores guardados como jobs."""

    def __init__(self, db):
        self.db = db
        self.email_service = EmailService()
        self.archive_service = PaymentProviderArchiveService(db)

    def process(self, batch_id: UUID, task_id: str) -> dict:
        batch = (
            self.db.query(JobBatch)
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

        now = datetime.now(timezone.utc)
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
                    JobBatch.started_at: func.coalesce(JobBatch.started_at, now),
                    JobBatch.heartbeat_at: now,
                },
                synchronize_session=False,
            )
        )
        if not claimed:
            self.db.rollback()
            return {"status": "not_claimed"}

        (
            self.db.query(Job)
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
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(batch.job)

        if self._is_cancel_requested(batch.job):
            self._cancel_pending(batch)
            return {"status": JobBatchStatus.CANCELLED.value}

        for item in batch.items:
            if item.status != JobItemStatus.PENDING.value:
                continue
            self.db.refresh(batch.job, attribute_names=["status"])
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
            self.db.query(JobBatch)
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
        self.db.commit()
        JobService(self.db).refresh_progress(batch.job_id)

    def _process_item(self, batch: JobBatch, item: JobItem) -> None:
        payload = item.result_data or {}
        item.status = JobItemStatus.RUNNING.value
        item.attempts += 1
        item.started_at = datetime.now(timezone.utc)
        batch.heartbeat_at = item.started_at
        self.db.commit()

        try:
            attachments = self._build_attachments(payload.get("attachments", []))
            message = self.email_service.build_from_template(
                template=PayloadMailingParameter(payload["mailing_parameter"]),
                parameters=payload["parameters"],
                subject=payload.get("subject"),
                body_override=payload.get("message_override"),
                to=payload["to"],
                cc=payload.get("cc"),
                bcc=payload.get("bcc"),
                attachments=attachments,
            )
            self.email_service.send(message, self.db)
            item.status = JobItemStatus.SUCCEEDED.value
            item.external_status_code = 200
            item.safe_error = None
            item.result_data = {
                "provider_id": payload.get("provider_id"),
                "provider": payload.get("provider"),
                "subject": message.subject,
                "to": message.to,
                "cc": message.cc,
                "bcc": message.bcc,
                "attachments": [attachment.filename for attachment in attachments],
                "message": "Correo enviado correctamente",
                **self._archive_sent_attachments(batch, item, payload),
            }
        except Exception as exc:
            item.status = JobItemStatus.FAILED.value
            item.safe_error = str(exc)[:2000]

        item.finished_at = datetime.now(timezone.utc)
        self._increment_progress(
            batch,
            succeeded=item.status == JobItemStatus.SUCCEEDED.value,
            failed=item.status == JobItemStatus.FAILED.value,
        )
        self.db.commit()

    @staticmethod
    def _build_attachments(items: list[dict]) -> list[EmailAttachment]:
        attachments = []
        for item in items:
            file_path = Path(item["file_path"])
            attachments.append(
                EmailAttachment(
                    filename=item["filename"],
                    content=file_path.read_bytes(),
                    content_type=item.get("content_type") or "application/pdf",
                )
            )
        return attachments

    def _archive_sent_attachments(
        self,
        batch: JobBatch,
        item: JobItem,
        payload: dict,
    ) -> dict:
        """Mueve las constancias al archivo permanente. Nunca tumba el envio.

        Si el archivado falla el correo YA salio, asi que el item sigue siendo
        exitoso: se anota el error y el PDF se queda en el staging para que la
        limpieza lo recoja mas adelante.
        """
        try:
            archived = self.archive_service.archive_item_attachments(
                item.id,
                payload.get("attachments", []),
                user_id=batch.job.created_by,
            )
            return {
                "archived_attachment_ids": [str(row.id) for row in archived],
            }
        except Exception as error:
            logger.exception(
                "Correo enviado pero no se pudo archivar la constancia del item %s",
                item.id,
            )
            return {"archive_error": str(error)[:500]}

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
        self.db.commit()
        JobService(self.db).refresh_progress(batch.job_id)

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
    def _is_cancel_requested(job: Job) -> bool:
        return job.status in {
            JobStatus.CANCEL_REQUESTED.value,
            JobStatus.CANCELLED.value,
        }


class PayloadMailingParameter:
    """Adaptador pequeno para reutilizar EmailService sin consultar BD por item."""

    def __init__(self, data: dict):
        self.name = data.get("name")
        self.template = data.get("template")
        self.template_html = data.get("template_html")
        self.template_text = data.get("template_text")
        self.mp_from = data.get("mp_from")
        self.to = data.get("to")
        self.subject = data.get("subject")
        self.cc = data.get("cc")
        self.bcc = data.get("bcc")
