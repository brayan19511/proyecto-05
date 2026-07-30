from datetime import datetime
from typing import Any
from uuid import UUID

from app.api.jobs.constants import (
    JobBatchStatus,
    JobItemStatus,
    JobStatus,
    JobTriggerSource,
    JobType,
)
from app.core.schemas import ORMModel, PageResponse


class JobBatchResponse(ORMModel):
    id: UUID
    sequence: int
    status: JobBatchStatus
    attempts: int
    total_items: int
    succeeded_items: int
    failed_items: int
    cancelled_items: int
    started_at: datetime | None
    finished_at: datetime | None
    heartbeat_at: datetime | None
    error_summary: str | None


class JobSummaryResponse(ORMModel):
    id: UUID
    parent_job_id: UUID | None
    scheduled_job_id: UUID | None
    trigger_source: JobTriggerSource
    job_type: JobType
    status: JobStatus
    created_by: UUID | None
    creator_email: str | None
    total_items: int
    processed_items: int
    succeeded_items: int
    failed_items: int
    cancelled_items: int
    total_batches: int
    finished_batches: int
    progress_percentage: float
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancel_requested_at: datetime | None


class JobDetailResponse(JobSummaryResponse):
    parameters: dict[str, Any]
    error_summary: str | None
    batches: list[JobBatchResponse]


# Listado paginado estándar (ver app/core/schemas.py).
JobPageResponse = PageResponse[JobSummaryResponse]


class JobItemResponse(ORMModel):
    id: UUID
    batch_id: UUID
    reference: str
    status: JobItemStatus
    attempts: int
    external_status_code: int | None
    result_data: dict | list | str | None
    safe_error: str | None
    started_at: datetime | None
    finished_at: datetime | None


JobItemPageResponse = PageResponse[JobItemResponse]
