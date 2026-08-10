from datetime import datetime, timezone
import json
import time
import uuid
from app.core.config import settings

from fastapi import BackgroundTasks, Request
from fastapi.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.audit_utils import get_client_ip, get_request_body
from app.core.audit_utils import audit_steps_context
from app.services.audit.audit_service import AuditService


SENSITIVE_HEADER_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
}

SENSITIVE_BODY_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "document_number",
    "document_numbers",
    "documentos",
    "references",
}

SENSITIVE_QUERY_KEYS = {
    "document_number",
    "document_numbers",
}

REDACT_RESPONSE_BODY_PATH_PREFIXES = {
    "/api/attendance",
    "/api/jobs",
    "/api/sap",
}

FILE_CONTENT_KEYS = {
    "file_base64",
    "base64",
    "content_base64",
    "file_content",
}


def sanitize_headers(headers: dict) -> dict:
    return {
        key: ("[REDACTED]" if key.lower() in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_query_params(query_params) -> dict:
    """Preserve repeated query parameters while redacting sensitive values."""
    items = (
        query_params.multi_items()
        if hasattr(query_params, "multi_items")
        else query_params.items()
    )
    sanitized = {}

    for key, value in items:
        safe_value = (
            "[REDACTED]"
            if key.lower() in SENSITIVE_QUERY_KEYS
            else value
        )
        if key not in sanitized:
            sanitized[key] = safe_value
        elif isinstance(sanitized[key], list):
            sanitized[key].append(safe_value)
        else:
            sanitized[key] = [sanitized[key], safe_value]

    return sanitized


def sanitize_payload(value):
    if isinstance(value, dict):
        sanitized = {}

        for key, item in value.items():
            normalized_key = key.lower()

            if normalized_key in FILE_CONTENT_KEYS:
                sanitized[key] = "[FILE_CONTENT_OMITTED]"
                continue

            if normalized_key in SENSITIVE_BODY_KEYS:
                sanitized[key] = "[REDACTED]"
                continue

            sanitized[key] = sanitize_payload(item)

        return sanitized

    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]

    return value


class AuditMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # =====================================================
        # INICIO DE TRAZA
        # =====================================================

        start_time_dt = datetime.now(timezone.utc)
        start_time_float = time.time()

        trace_id = str(uuid.uuid4())

        request.state.trace_id = trace_id

        # Contexto donde los servicios van agregando pasos
        local_steps = []
        token = audit_steps_context.set(local_steps)

        # =====================================================
        # DATOS BÁSICOS DEL REQUEST
        # =====================================================

        method = request.method
        path = request.url.path

        query_params = sanitize_query_params(request.query_params)

        client_ip = get_client_ip(request)

        user_agent = request.headers.get("user-agent")

        # =====================================================
        # REQUEST BODY
        # =====================================================

        req_body = None

        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await get_request_body(request)

                req_body = json.loads(body_bytes) if body_bytes else None
                req_body = sanitize_payload(req_body)

            except Exception:
                req_body = {"error": "Could not parse body"}

        # =====================================================
        # CREA AUDITORÍA INICIAL (RUNNING)
        # =====================================================

        audit_id = AuditService.start_audit(
            {
                "trace_id": trace_id,
                # "user_id": user_id,
                "method": method,
                "path": path,
                "environment": settings.ENV,
                "started_at": start_time_dt,
            }
        )

        request.state.audit_id = audit_id

        # =====================================================
        # EJECUCIÓN DEL ENDPOINT
        # =====================================================

        try:

            response = await call_next(request)

        except Exception as exc:

            audit_steps_capturados = list(local_steps)

            audit_steps_context.reset(token)

            # Finaliza inmediatamente la auditoría como ERROR
            AuditService.finish_audit(
                audit_id=audit_id,
                header_updates={
                    "status_code": 500,
                    "finished_at": datetime.now(timezone.utc),
                },
                detail_data={
                    "level": "ERROR",
                    "error_message": str(exc),
                    "error_stack": getattr(request.state, "error_stack", None),
                },
                steps_data=audit_steps_capturados,
            )

            raise

        # =====================================================
        # RECUPERAR PASOS CAPTURADOS
        # =====================================================

        audit_steps_capturados = list(local_steps)

        audit_steps_context.reset(token)

        # =====================================================
        # DATOS DE RESPUESTA
        # =====================================================

        content_length = response.headers.get("content-length")

        if not content_length and hasattr(response, "body"):
            content_length = len(response.body)

        try:
            response_size = int(content_length) if content_length else 0
        except (ValueError, TypeError):
            response_size = 0

        end_time_dt = datetime.now(timezone.utc)

        duration_ms = (time.time() - start_time_float) * 1000

        # =====================================================
        # RESPONSE BODY
        # =====================================================

        response_body = None

        redact_response_body = any(
            path.startswith(prefix)
            for prefix in REDACT_RESPONSE_BODY_PATH_PREFIXES
        )

        if redact_response_body:
            response_body = {"info": "[REDACTED]"}
        elif "application/json" in response.headers.get("content-type", ""):

            response_body_bytes = [section async for section in response.body_iterator]

            response.body_iterator = iterate_in_threadpool(iter(response_body_bytes))

            try:
                # Unir todos los chunks: una respuesta JSON puede venir
                # fragmentada en varias secciones y decodificar solo la
                # primera registraria un JSON parcial o invalido.
                raw_body = b"".join(response_body_bytes)
                response_body = json.loads(raw_body.decode())
                response_body = sanitize_payload(response_body)
            except Exception:
                response_body = {"info": "Body no serializable"}

        # =====================================================
        # NIVEL DE AUDITORÍA
        # =====================================================

        level = "INFO"

        if response.status_code >= 400:
            level = "WARNING"

        if response.status_code >= 500:
            level = "ERROR"

        error_msg = getattr(request.state, "error_message", None)

        error_stk = getattr(request.state, "error_stack", None)

        # =====================================================
        # FINALIZAR AUDITORÍA EN BACKGROUND
        # =====================================================

        background_tasks = BackgroundTasks()

        background_tasks.add_task(
            AuditService.finish_audit,
            audit_id,
            {
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "finished_at": end_time_dt,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "user_id": getattr(request.state, "user_id", None),
            },
            {
                "request_headers": sanitize_headers(dict(request.headers)),
                "query_params": query_params,
                "request_body": req_body,
                "response_body": response_body,
                "level": level,
                "error_message": error_msg,
                "error_stack": error_stk,
                "response_size_bytes": response_size,
            },
            audit_steps_capturados,
        )

        response.background = background_tasks

        return response
