from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.observability.constants import LOGIN_PATH_SUFFIX


class ObservabilityRepository:
    """Consultas de agregacion de solo lectura sobre audit.* y jobs.*.

    Se usan sentencias SQL con parametros ligados (nunca interpolacion) porque
    las agregaciones (percentiles, count FILTER) son mas claras y eficientes
    escritas directamente que armadas con el ORM.
    """

    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # LOGS
    # =====================================================
    def logs_totals(self, date_from: datetime, date_to: datetime) -> dict:
        row = self.db.execute(
            text(
                """
                SELECT
                    count(*) AS total,
                    avg(duration_ms) AS avg_ms,
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
                    count(*) FILTER (WHERE status_code >= 500) AS c5xx,
                    count(*) FILTER (WHERE status_code >= 400 AND status_code < 500) AS c4xx,
                    count(*) FILTER (WHERE status_code < 400) AS c2xx
                FROM audit.logs
                WHERE created_at >= :date_from AND created_at < :date_to
                """
            ),
            {"date_from": date_from, "date_to": date_to},
        ).mappings().one()
        return dict(row)

    def logs_by_level(self, date_from: datetime, date_to: datetime) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT coalesce(d.level, 'INFO') AS label, count(*) AS count
                FROM audit.logs l
                LEFT JOIN audit.log_details d ON d.log_id = l.id
                WHERE l.created_at >= :date_from AND l.created_at < :date_to
                GROUP BY coalesce(d.level, 'INFO')
                ORDER BY count DESC
                """
            ),
            {"date_from": date_from, "date_to": date_to},
        ).mappings().all()
        return [dict(row) for row in rows]

    def logs_by_endpoint(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        order_by: str,
        limit: int,
    ) -> list[dict]:
        # order_by ya viene validado por el router (lista blanca), asi que es
        # seguro elegir la columna de ordenamiento aqui.
        order_column = {
            "requests": "requests DESC",
            "avg_duration": "avg_ms DESC NULLS LAST",
            "errors": "error_count DESC",
        }[order_by]
        rows = self.db.execute(
            text(
                f"""
                SELECT
                    method,
                    path,
                    count(*) AS requests,
                    avg(duration_ms) AS avg_ms,
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
                    count(*) FILTER (WHERE status_code >= 500) AS error_count
                FROM audit.logs
                WHERE created_at >= :date_from AND created_at < :date_to
                GROUP BY method, path
                ORDER BY {order_column}
                LIMIT :limit
                """
            ),
            {"date_from": date_from, "date_to": date_to, "limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]

    def error_logs(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        where = (
            "l.created_at >= :date_from AND l.created_at < :date_to "
            "AND (coalesce(d.level, 'INFO') IN ('ERROR', 'CRITICAL') "
            "OR l.status_code >= 500)"
        )
        params = {"date_from": date_from, "date_to": date_to}

        total = self.db.execute(
            text(
                f"""
                SELECT count(*)
                FROM audit.logs l
                LEFT JOIN audit.log_details d ON d.log_id = l.id
                WHERE {where}
                """
            ),
            params,
        ).scalar_one()

        rows = self.db.execute(
            text(
                f"""
                SELECT
                    l.id, l.trace_id, coalesce(d.level, 'INFO') AS level,
                    l.method, l.path, l.status_code, d.error_message,
                    l.duration_ms, l.user_id, l.created_at
                FROM audit.logs l
                LEFT JOIN audit.log_details d ON d.log_id = l.id
                WHERE {where}
                ORDER BY l.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(row) for row in rows], total

    def auth_totals(self, date_from: datetime, date_to: datetime) -> dict:
        row = self.db.execute(
            text(
                """
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE status_code < 400) AS succeeded,
                    count(*) FILTER (WHERE status_code >= 400) AS failed,
                    count(DISTINCT user_id) AS distinct_users,
                    count(DISTINCT ip_address) AS distinct_ips
                FROM audit.logs
                WHERE created_at >= :date_from AND created_at < :date_to
                  AND method = 'POST'
                  AND path LIKE :login_pattern
                """
            ),
            {
                "date_from": date_from,
                "date_to": date_to,
                "login_pattern": f"%{LOGIN_PATH_SUFFIX}",
            },
        ).mappings().one()
        return dict(row)

    # =====================================================
    # JOBS / WORKERS
    # =====================================================
    def jobs_by_type(self, date_from: datetime, date_to: datetime) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT
                    job_type,
                    count(*) AS total,
                    count(*) FILTER (WHERE status = 'COMPLETED') AS succeeded,
                    count(*) FILTER (
                        WHERE status IN ('FAILED', 'DISPATCH_FAILED')
                    ) AS failed,
                    count(*) FILTER (WHERE status = 'RUNNING') AS running,
                    avg(
                        EXTRACT(EPOCH FROM (finished_at - started_at))
                    ) FILTER (
                        WHERE finished_at IS NOT NULL AND started_at IS NOT NULL
                    ) AS avg_seconds
                FROM jobs.jobs
                WHERE created_at >= :date_from AND created_at < :date_to
                GROUP BY job_type
                ORDER BY total DESC
                """
            ),
            {"date_from": date_from, "date_to": date_to},
        ).mappings().all()
        return [dict(row) for row in rows]

    # =====================================================
    # SCHEDULER (salud de tareas programadas)
    # =====================================================
    def scheduler_health(self) -> dict:
        row = self.db.execute(
            text(
                """
                SELECT
                    max(last_run_at) AS last_run_at,
                    count(*) FILTER (WHERE consecutive_failures > 0) AS failing
                FROM jobs.scheduled_jobs
                WHERE enabled IS TRUE
                """
            )
        ).mappings().one()
        return dict(row)
