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

    def logs_top_users(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        limit: int,
    ) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT user_id::text AS label, count(*) AS count
                FROM audit.logs
                WHERE created_at >= :date_from AND created_at < :date_to
                  AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT :limit
                """
            ),
            {"date_from": date_from, "date_to": date_to, "limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]

    def logs_top_ips(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        limit: int,
    ) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT ip_address AS label, count(*) AS count
                FROM audit.logs
                WHERE created_at >= :date_from AND created_at < :date_to
                  AND ip_address IS NOT NULL
                GROUP BY ip_address
                ORDER BY count DESC
                LIMIT :limit
                """
            ),
            {"date_from": date_from, "date_to": date_to, "limit": limit},
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

    def list_requests(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        level: str | None,
        status_class: str | None,
        method: str | None,
        path_contains: str | None,
        user_id: str | None,
        min_duration_ms: float | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        # Se arma el WHERE con parametros ligados; ningun valor se interpola.
        conditions = ["l.created_at >= :date_from", "l.created_at < :date_to"]
        params: dict = {"date_from": date_from, "date_to": date_to}

        if level:
            conditions.append("coalesce(d.level, 'INFO') = :level")
            params["level"] = level
        if status_class:
            low = int(status_class[0]) * 100
            conditions.append("l.status_code >= :sc_low AND l.status_code < :sc_high")
            params["sc_low"] = low
            params["sc_high"] = low + 100
        if method:
            conditions.append("l.method = :method")
            params["method"] = method
        if path_contains:
            conditions.append("l.path LIKE :path_like")
            params["path_like"] = f"%{path_contains}%"
        if user_id:
            conditions.append("l.user_id = :user_id")
            params["user_id"] = user_id
        if min_duration_ms is not None:
            conditions.append("l.duration_ms >= :min_dur")
            params["min_dur"] = min_duration_ms

        where = " AND ".join(conditions)

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
                    l.method, l.path, l.status_code, l.duration_ms,
                    l.user_id, l.ip_address, d.error_message, l.created_at
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

    def get_request_detail(self, log_id: str) -> dict | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    l.id, l.trace_id, l.method, l.path, l.status_code,
                    coalesce(d.level, 'INFO') AS level, l.duration_ms,
                    l.user_id, l.ip_address, l.user_agent, l.environment,
                    l.started_at, l.finished_at, l.created_at,
                    d.request_headers, d.query_params, d.request_body,
                    d.response_body, d.response_size_bytes,
                    d.error_message, d.error_stack
                FROM audit.logs l
                LEFT JOIN audit.log_details d ON d.log_id = l.id
                WHERE l.id = :log_id
                """
            ),
            {"log_id": log_id},
        ).mappings().first()
        return dict(row) if row else None

    def get_request_steps(self, log_id: str) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT step_order, step_name, status, message,
                       duration_ms, extra_data
                FROM audit.log_steps
                WHERE log_id = :log_id
                ORDER BY step_order
                """
            ),
            {"log_id": log_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_auth_events(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        where = (
            "created_at >= :date_from AND created_at < :date_to "
            "AND method = 'POST' AND path LIKE :login_pattern"
        )
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "login_pattern": f"%{LOGIN_PATH_SUFFIX}",
        }

        total = self.db.execute(
            text(f"SELECT count(*) FROM audit.logs WHERE {where}"),
            params,
        ).scalar_one()

        rows = self.db.execute(
            text(
                f"""
                SELECT
                    id, user_id, ip_address, user_agent, status_code,
                    (status_code < 400) AS succeeded, created_at
                FROM audit.logs
                WHERE {where}
                ORDER BY created_at DESC
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
