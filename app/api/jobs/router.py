from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.jobs.constants import (
    JOBS_CANCEL_ALL_PERMISSION,
    JOBS_CANCEL_PERMISSION,
    JOBS_RETRY_PERMISSION,
    JOBS_VIEW_ALL_PERMISSION,
    JOBS_VIEW_PERMISSION,
    JobItemStatus,
    JobStatus,
    JobType,
)
from app.api.jobs.schemas import (
    JobDetailResponse,
    JobItemPageResponse,
    JobPageResponse,
)
from app.api.jobs.service import JobService
from app.core.access import (
    get_permission_codes,
    is_admin,
    require_any_permission,
)
from app.core.config import settings
from app.core.db.db_postgres import get_db
from app.workers.dispatcher import dispatch_job


router = APIRouter(prefix="/jobs", tags=["JOBS"])


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db, dispatcher=dispatch_job)


def _has_permission(user, permission: str) -> bool:
    return is_admin(user) or permission in get_permission_codes(user)


@router.get("", response_model=JobPageResponse)
def get_jobs(
    mine: bool = Query(default=True),
    job_type: JobType | None = Query(default=None),
    status: JobStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: JobService = Depends(get_job_service),
    current_user=Depends(
        require_any_permission(JOBS_VIEW_PERMISSION, JOBS_VIEW_ALL_PERMISSION),
    ),
):
    return service.list_jobs(
        current_user_id=current_user.id,
        can_view_all=_has_permission(current_user, JOBS_VIEW_ALL_PERMISSION),
        mine=mine,
        job_type=job_type.value if job_type else None,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    current_user=Depends(
        require_any_permission(JOBS_VIEW_PERMISSION, JOBS_VIEW_ALL_PERMISSION),
    ),
):
    return service.get_job(
        job_id,
        user_id=current_user.id,
        can_view_all=_has_permission(current_user, JOBS_VIEW_ALL_PERMISSION),
    )


@router.get("/{job_id}/items", response_model=JobItemPageResponse)
def get_job_items(
    job_id: UUID,
    item_status: JobItemStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: JobService = Depends(get_job_service),
    current_user=Depends(
        require_any_permission(JOBS_VIEW_PERMISSION, JOBS_VIEW_ALL_PERMISSION),
    ),
):
    return service.list_items(
        job_id,
        user_id=current_user.id,
        can_view_all=_has_permission(current_user, JOBS_VIEW_ALL_PERMISSION),
        status=item_status.value if item_status else None,
        limit=limit,
        offset=offset,
    )


@router.post("/{job_id}/cancel", response_model=JobDetailResponse)
def cancel_job(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    current_user=Depends(
        require_any_permission(
            JOBS_CANCEL_PERMISSION,
            JOBS_CANCEL_ALL_PERMISSION,
        ),
    ),
):
    return service.cancel_job(
        job_id,
        user_id=current_user.id,
        can_cancel_all=_has_permission(
            current_user,
            JOBS_CANCEL_ALL_PERMISSION,
        ),
    )


@router.post("/{job_id}/retry", response_model=JobDetailResponse)
def retry_job(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    current_user=Depends(require_any_permission(JOBS_RETRY_PERMISSION)),
):
    return service.retry_job(
        job_id,
        user_id=current_user.id,
        can_retry_all=_has_permission(current_user, JOBS_VIEW_ALL_PERMISSION),
        batch_size=settings.SAP_JOB_BATCH_SIZE,
    )
