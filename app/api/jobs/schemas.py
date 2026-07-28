from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.jobs.constants import (
    JobBatchStatus,
    JobItemStatus,
    JobStatus,
    JobTriggerSource,
    JobType,
)


class JobBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class JobSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class JobPageResponse(BaseModel):
    items: list[JobSummaryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class JobItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class JobItemPageResponse(BaseModel):
    items: list[JobItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
