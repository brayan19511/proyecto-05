from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.api.observability.repository import ObservabilityRepository
from app.api.observability.schemas import (
    AuthStatsResponse,
    EndpointStat,
    EndpointStatsResponse,
    ErrorLogItem,
    ErrorLogPageResponse,
    JobsSummaryResponse,
    JobTypeStat,
    LabelCount,
    LogsSummaryResponse,
)
from app.core.exceptions import ValidationError


# Rango por defecto cuando el cliente no envia fechas, y tope maximo para que
# una consulta no barra un historial demasiado grande.
DEFAULT_WINDOW_HOURS = 24
MAX_WINDOW_DAYS = 92


def _as_utc(value: datetime) -> datetime:
    # Una fecha sin zona horaria se interpreta como UTC para comparar de forma
    # consistente contra columnas timestamptz.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def resolve_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[datetime, datetime]:
    """Normaliza el rango [date_from, date_to) y valida sus limites."""
    now = datetime.now(timezone.utc)
    end = _as_utc(date_to) if date_to else now
    start = _as_utc(date_from) if date_from else (end - timedelta(hours=DEFAULT_WINDOW_HOURS))
    if start >= end:
        raise ValidationError("date_from debe ser anterior a date_to")
    if end - start > timedelta(days=MAX_WINDOW_DAYS):
        raise ValidationError(
            f"El rango no puede superar {MAX_WINDOW_DAYS} dias"
        )
    return start, end


class ObservabilityAnalyticsService:
    """Agregaciones de logs y jobs para analisis operativo."""

    def __init__(self, db: Session):
        self.repository = ObservabilityRepository(db)

    def logs_summary(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> LogsSummaryResponse:
        totals = self.repository.logs_totals(date_from, date_to)
        levels = self.repository.logs_by_level(date_from, date_to)

        total = totals["total"] or 0
        c5xx = totals["c5xx"] or 0
        return LogsSummaryResponse(
            date_from=date_from,
            date_to=date_to,
            total_requests=total,
            by_level=[
                LabelCount(label=row["label"], count=row["count"]) for row in levels
            ],
            by_status_class=[
                LabelCount(label="2xx", count=totals["c2xx"] or 0),
                LabelCount(label="4xx", count=totals["c4xx"] or 0),
                LabelCount(label="5xx", count=c5xx),
            ],
            error_rate=round(c5xx / total, 4) if total else 0.0,
            avg_duration_ms=self._round(totals["avg_ms"]),
            p95_duration_ms=self._round(totals["p95_ms"]),
        )

    def endpoint_stats(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        sort: str,
        limit: int,
    ) -> EndpointStatsResponse:
        rows = self.repository.logs_by_endpoint(
            date_from,
            date_to,
            order_by=sort,
            limit=limit,
        )
        return EndpointStatsResponse(
            date_from=date_from,
            date_to=date_to,
            items=[
                EndpointStat(
                    method=row["method"],
                    path=row["path"],
                    requests=row["requests"],
                    avg_duration_ms=self._round(row["avg_ms"]),
                    p95_duration_ms=self._round(row["p95_ms"]),
                    error_count=row["error_count"],
                )
                for row in rows
            ],
        )

    def error_logs(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        limit: int,
        offset: int,
    ) -> ErrorLogPageResponse:
        rows, total = self.repository.error_logs(
            date_from,
            date_to,
            limit=limit,
            offset=offset,
        )
        items = [ErrorLogItem(**row) for row in rows]
        return ErrorLogPageResponse.build(items, total, limit, offset)

    def auth_stats(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> AuthStatsResponse:
        totals = self.repository.auth_totals(date_from, date_to)
        return AuthStatsResponse(
            date_from=date_from,
            date_to=date_to,
            total_attempts=totals["total"] or 0,
            succeeded=totals["succeeded"] or 0,
            failed=totals["failed"] or 0,
            distinct_users=totals["distinct_users"] or 0,
            distinct_ips=totals["distinct_ips"] or 0,
        )

    def jobs_summary(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> JobsSummaryResponse:
        rows = self.repository.jobs_by_type(date_from, date_to)
        total = sum(row["total"] for row in rows)
        failed = sum(row["failed"] for row in rows)
        return JobsSummaryResponse(
            date_from=date_from,
            date_to=date_to,
            total_jobs=total,
            failure_rate=round(failed / total, 4) if total else 0.0,
            by_type=[
                JobTypeStat(
                    job_type=row["job_type"],
                    total=row["total"],
                    succeeded=row["succeeded"],
                    failed=row["failed"],
                    running=row["running"],
                    avg_duration_seconds=self._round(row["avg_seconds"]),
                )
                for row in rows
            ],
        )

    @staticmethod
    def _round(value) -> float | None:
        return round(float(value), 2) if value is not None else None
