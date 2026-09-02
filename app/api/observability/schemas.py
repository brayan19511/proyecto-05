from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.schemas import PageResponse


# =====================================================
# ESTADO DEL SISTEMA (/observability/status)
# =====================================================
class ComponentStatus(BaseModel):
    """Resultado del chequeo de un componente (DB, workers, SMTP, etc.)."""

    component: str
    status: str  # ok | disabled | degraded | down
    latency_ms: float | None = None
    detail: str | None = None


class SystemStatusResponse(BaseModel):
    status: str  # estado global = el peor de los componentes
    checked_at: datetime
    components: list[ComponentStatus]


# =====================================================
# ANALITICA DE LOGS (/observability/logs/*)
# =====================================================
class LabelCount(BaseModel):
    """Par etiqueta/conteo reutilizable (por nivel, por clase de estado...)."""

    label: str
    count: int


class LogsSummaryResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    total_requests: int
    by_level: list[LabelCount]
    by_status_class: list[LabelCount]
    # error_rate = proporcion de respuestas 5xx sobre el total (0..1).
    error_rate: float
    avg_duration_ms: float | None
    p95_duration_ms: float | None
    # Recurrencia: usuarios e IPs con mas peticiones en el rango.
    # En top_users, label = user_id (UUID como texto).
    top_users: list[LabelCount]
    top_ips: list[LabelCount]


class EndpointStat(BaseModel):
    method: str
    path: str
    requests: int
    avg_duration_ms: float | None
    p95_duration_ms: float | None
    error_count: int


class EndpointStatsResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    items: list[EndpointStat]


class ErrorLogItem(BaseModel):
    id: UUID
    trace_id: str
    level: str
    method: str
    path: str
    status_code: int | None
    error_message: str | None
    duration_ms: float | None
    user_id: UUID | None
    created_at: datetime


ErrorLogPageResponse = PageResponse[ErrorLogItem]


class AuthStatsResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    total_attempts: int
    succeeded: int
    failed: int
    distinct_users: int
    distinct_ips: int


# =====================================================
# DRILL-DOWN: navegar peticiones y ver su detalle
# =====================================================
class RequestLogItem(BaseModel):
    """Fila resumida para el listado navegable de peticiones."""

    id: UUID
    trace_id: str
    level: str
    method: str
    path: str
    status_code: int | None
    duration_ms: float | None
    user_id: UUID | None
    ip_address: str | None
    error_message: str | None
    created_at: datetime


RequestLogPageResponse = PageResponse[RequestLogItem]


class AuditStepItem(BaseModel):
    step_order: int
    step_name: str
    status: str
    message: str | None
    duration_ms: float | None
    extra_data: dict | list | None


class RequestLogDetail(BaseModel):
    """Detalle completo de una peticion (cabecera + cuerpos + pasos)."""

    id: UUID
    trace_id: str
    method: str
    path: str
    status_code: int | None
    level: str
    duration_ms: float | None
    user_id: UUID | None
    ip_address: str | None
    user_agent: str | None
    environment: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    # Contenido pesado (ya sanitizado al capturarse en el middleware).
    request_headers: dict | None
    query_params: dict | None
    request_body: dict | list | None
    response_body: dict | list | None
    response_size_bytes: int | None
    error_message: str | None
    error_stack: str | None
    steps: list[AuditStepItem]


class AuthEventItem(BaseModel):
    """Un intento de login individual."""

    id: UUID
    user_id: UUID | None
    ip_address: str | None
    user_agent: str | None
    status_code: int | None
    succeeded: bool
    created_at: datetime


AuthEventPageResponse = PageResponse[AuthEventItem]


# =====================================================
# ANALITICA DE JOBS/WORKERS (/observability/jobs/summary)
# =====================================================
class JobTypeStat(BaseModel):
    job_type: str
    total: int
    succeeded: int
    failed: int
    running: int
    avg_duration_seconds: float | None


class JobsSummaryResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    total_jobs: int
    # failure_rate = jobs fallidos sobre el total en el rango (0..1).
    failure_rate: float
    by_type: list[JobTypeStat]
