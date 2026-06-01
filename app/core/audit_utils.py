# app/core/audit_utils.py
from starlette.requests import Request
from contextvars import ContextVar
from typing import List, Dict, Any

audit_steps_context: ContextVar[List[Dict[str, Any]]] = ContextVar("audit_steps_context")

async def get_request_body(request: Request):
    body = await request.body()
    # Re-inyectamos el body para que otros lo puedan leer
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive
    return body
def add_step(name: str, status: str = "INFO", message: str = None, duration: float = 0):
    try:
        # Intentamos obtener la lista del contexto de la petición actual
        steps = audit_steps_context.get()
        step_order = len(steps) + 1
        steps.append({
            "step_name": name,
            "step_order": step_order,
            "status": status,
            "message": message,
            "duration_ms": duration
        })
    except LookupError:
        # Si el servicio se ejecuta fuera de un entorno HTTP (ej: un script cron o testing)
        # evitamos que rompa imprimiendo la auditoría en consola o logs tradicionales
        print(f"[{status}] {name}: {message}")