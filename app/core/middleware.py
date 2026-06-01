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
        # 1. ANTES del proceso: Inicio de traza
        start_time_dt = datetime.now(timezone.utc)
        start_time_float = time.time()
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        request.state.audit_steps = []

        # Inicializamos el ContextVar para esta petición específica
        local_steps = []
        token = audit_steps_context.set(local_steps)

        # Captura inicial de datos de la petición
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        req_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await get_request_body(request)
                req_body = json.loads(body_bytes) if body_bytes else None
            except:
                req_body = {"error": "Could not parse body"}

        # 2. EJECUCIÓN DEL FLUJO CON MÁXIMA SEGURIDAD
        try:
            response = await call_next(request)
        except Exception as exc:
            # Si el endpoint explota antes de generar un response (Error 500 no controlado por FastAPI)
            # Forzamos la recuperación de pasos para no perder la traza del error
            audit_steps_capturados = list(local_steps)
            audit_steps_context.reset(token)
            # Re-lanzamos la excepción para que FastAPI la procese o use tus handlers
            raise exc
        else:
            # Si el flujo terminó de manera normal (Con éxito, Warning o Error controlado),
            # recuperamos los pasos y limpiamos el contexto de forma segura.
            audit_steps_capturados = list(local_steps)
            audit_steps_context.reset(token)

        # 3. PROCESAMIENTO POSTERIOR DE LA RESPUESTA
        content_length = response.headers.get("content-length")
        if not content_length and hasattr(response, "body"):
            content_length = len(response.body)
        try:
            response_size = int(content_length) if content_length else 0
        except (ValueError, TypeError):
            response_size = 0

        end_time_dt = datetime.now(timezone.utc)
        duration_ms = (time.time() - start_time_float) * 1000

        response_body = None
        if "application/json" in response.headers.get("content-type", ""):
            response_body_bytes = [section async for section in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body_bytes))
            try:
                response_body = json.loads(response_body_bytes[0].decode())
            except:
                response_body = {"info": "Body no serializable"}

        error_msg = getattr(request.state, "error_message", None)
        error_stk = getattr(request.state, "error_stack", None)

        level = "INFO"
        if response.status_code >= 400:
            level = "WARNING"
        if response.status_code >= 500:
            level = "ERROR"

        user_id = getattr(request.state, "user_id", None)

        # Estructura final del JSON de auditoría
        audit_data = {
            "log_header": {
                "trace_id": trace_id,
                "user_id": user_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "ip_address": client_ip,
                "user_agent": user_agent,
                "started_at": start_time_dt,
                "finished_at": end_time_dt,
                "environment": settings.ENV,
            },
            "log_detail": {
                "request_headers": dict(request.headers),
                "query_params": query_params,
                "request_body": req_body,
                "response_body": response_body,
                "level": level,
                "error_message": error_msg,
                "error_stack": error_stk,
                "response_size_bytes": response_size,
            },
            "steps": audit_steps_capturados,  # Guardará los pasos tanto en éxitos como en fallas
        }

        # 4. GUARDADO ASÍNCRONO
        background_tasks = BackgroundTasks()
        background_tasks.add_task(AuditService.save_audit, audit_data)
        response.background = background_tasks

        return response
