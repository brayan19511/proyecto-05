from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.jobs.constants import (
    SCHEDULED_JOBS_EDIT_PERMISSION,
    SCHEDULED_JOBS_RUN_PERMISSION,
    SCHEDULED_JOBS_VIEW_PERMISSION,
)
from app.api.jobs.schemas import JobDetailResponse
from app.api.scheduled_jobs.schemas import (
    ScheduledJobCreate,
    ScheduledJobPageResponse,
    ScheduledJobResponse,
    ScheduledJobUpdate,
)
from app.api.scheduled_jobs.service import ScheduledJobService
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db


router = APIRouter(prefix="/scheduled-jobs", tags=["SCHEDULED JOBS"])


def get_scheduled_job_service(db: Session = Depends(get_db)) -> ScheduledJobService:
    return ScheduledJobService(db)


@router.get("", response_model=ScheduledJobPageResponse)
def list_scheduled_jobs(
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ScheduledJobService = Depends(get_scheduled_job_service),
    current_user=Depends(require_any_permission(SCHEDULED_JOBS_VIEW_PERMISSION)),
):
    return service.list_jobs(enabled=enabled, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scheduled_job(
    data: ScheduledJobCreate,
    service: ScheduledJobService = Depends(get_scheduled_job_service),
    current_user=Depends(require_any_permission(SCHEDULED_JOBS_EDIT_PERMISSION)),
):
    return service.create(data, user_id=current_user.id)


@router.get("/{scheduled_job_id}", response_model=ScheduledJobResponse)
def get_scheduled_job(
    scheduled_job_id: UUID,
    service: ScheduledJobService = Depends(get_scheduled_job_service),
    current_user=Depends(require_any_permission(SCHEDULED_JOBS_VIEW_PERMISSION)),
):
    return service.get(scheduled_job_id)


@router.patch("/{scheduled_job_id}", response_model=ScheduledJobResponse)
def update_scheduled_job(
    scheduled_job_id: UUID,
    data: ScheduledJobUpdate,
    service: ScheduledJobService = Depends(get_scheduled_job_service),
    current_user=Depends(require_any_permission(SCHEDULED_JOBS_EDIT_PERMISSION)),
):
    return service.update(scheduled_job_id, data, user_id=current_user.id)


@router.post(
    "/{scheduled_job_id}/run",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_scheduled_job_now(
    scheduled_job_id: UUID,
    service: ScheduledJobService = Depends(get_scheduled_job_service),
    current_user=Depends(require_any_permission(SCHEDULED_JOBS_RUN_PERMISSION)),
):
    return service.run_now(scheduled_job_id, user_id=current_user.id)
