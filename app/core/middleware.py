from datetime import datetime, timezone
import json
import time
import uuid
from app.core.config import settings

from fastapi import BackgroundTasks, Request
from fastapi.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.audit_utils import get_request_body
from app.core.audit_utils import audit_steps_context
from app.services.audit.audit_service import AuditService

class AuditMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

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

        query_params = dict(request.query_params)

        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        user_agent = request.headers.get("user-agent")

        user_id = getattr(
            request.state,
            "user_id",
            None
        )

        # =====================================================
        # REQUEST BODY
        # =====================================================

        req_body = None

        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await get_request_body(request)

                req_body = (
                    json.loads(body_bytes)
                    if body_bytes
                    else None
                )

            except Exception:
                req_body = {
                    "error": "Could not parse body"
                }

        # =====================================================
        # CREA AUDITORÍA INICIAL (RUNNING)
        # =====================================================

        audit_id = AuditService.start_audit(
            {
                "trace_id": trace_id,
                "user_id": user_id,
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
                    "error_stack": getattr(
                        request.state,
                        "error_stack",
                        None
                    ),
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

        content_length = response.headers.get(
            "content-length"
        )

        if (
            not content_length
            and hasattr(response, "body")
        ):
            content_length = len(response.body)

        try:
            response_size = (
                int(content_length)
                if content_length
                else 0
            )
        except (ValueError, TypeError):
            response_size = 0

        end_time_dt = datetime.now(timezone.utc)

        duration_ms = (
            time.time() - start_time_float
        ) * 1000

        # =====================================================
        # RESPONSE BODY
        # =====================================================

        response_body = None

        if "application/json" in response.headers.get(
            "content-type",
            ""
        ):

            response_body_bytes = [
                section
                async for section
                in response.body_iterator
            ]

            response.body_iterator = iterate_in_threadpool(
                iter(response_body_bytes)
            )

            try:
                response_body = json.loads(
                    response_body_bytes[0].decode()
                )
            except Exception:
                response_body = {
                    "info": "Body no serializable"
                }

        # =====================================================
        # NIVEL DE AUDITORÍA
        # =====================================================

        level = "INFO"

        if response.status_code >= 400:
            level = "WARNING"

        if response.status_code >= 500:
            level = "ERROR"

        error_msg = getattr(
            request.state,
            "error_message",
            None
        )

        error_stk = getattr(
            request.state,
            "error_stack",
            None
        )

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
            },
            {
                "request_headers": dict(request.headers),
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