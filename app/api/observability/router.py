from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.observability.analytics_service import (
    ObservabilityAnalyticsService,
    resolve_range,
)
from app.api.observability.constants import OBSERVABILITY_VIEW_PERMISSION
from app.api.observability.schemas import (
    AuthStatsResponse,
    EndpointStatsResponse,
    ErrorLogPageResponse,
    JobsSummaryResponse,
    LogsSummaryResponse,
    SystemStatusResponse,
)
from app.api.observability.status_service import SystemStatusService
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db


router = APIRouter(prefix="/observability", tags=["OBSERVABILIDAD"])

_require_view = require_any_permission(OBSERVABILITY_VIEW_PERMISSION)


def get_analytics_service(db: Session = Depends(get_db)) -> ObservabilityAnalyticsService:
    return ObservabilityAnalyticsService(db)


def get_status_service(db: Session = Depends(get_db)) -> SystemStatusService:
    return SystemStatusService(db)


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    service: SystemStatusService = Depends(get_status_service),
    _=Depends(_require_view),
):
    return service.get_status()


@router.get("/logs/summary", response_model=LogsSummaryResponse)
def get_logs_summary(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    service: ObservabilityAnalyticsService = Depends(get_analytics_service),
    _=Depends(_require_view),
):
    start, end = resolve_range(date_from, date_to)
    return service.logs_summary(start, end)


@router.get("/logs/endpoints", response_model=EndpointStatsResponse)
def get_logs_endpoints(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sort: Literal["requests", "avg_duration", "errors"] = Query(default="requests"),
    limit: int = Query(default=20, ge=1, le=100),
    service: ObservabilityAnalyticsService = Depends(get_analytics_service),
    _=Depends(_require_view),
):
    start, end = resolve_range(date_from, date_to)
    return service.endpoint_stats(start, end, sort=sort, limit=limit)


@router.get("/logs/errors", response_model=ErrorLogPageResponse)
def get_error_logs(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ObservabilityAnalyticsService = Depends(get_analytics_service),
    _=Depends(_require_view),
):
    start, end = resolve_range(date_from, date_to)
    return service.error_logs(start, end, limit=limit, offset=offset)


@router.get("/logs/auth", response_model=AuthStatsResponse)
def get_auth_stats(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    service: ObservabilityAnalyticsService = Depends(get_analytics_service),
    _=Depends(_require_view),
):
    start, end = resolve_range(date_from, date_to)
    return service.auth_stats(start, end)


@router.get("/jobs/summary", response_model=JobsSummaryResponse)
def get_jobs_summary(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    service: ObservabilityAnalyticsService = Depends(get_analytics_service),
    _=Depends(_require_view),
):
    start, end = resolve_range(date_from, date_to)
    return service.jobs_summary(start, end)
