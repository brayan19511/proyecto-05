from starlette.requests import Request
from contextvars import ContextVar
from typing import List, Dict, Any

audit_steps_context: ContextVar[List[Dict[str, Any]]] = ContextVar(
    "audit_steps_context"
)

async def get_request_body(request: Request):
    body = await request.body()

    async def receive():
        return {
            "type": "http.request",
            "body": body
        }

    request._receive = receive

    return body


def add_step(
    name: str,
    status: str = "INFO",
    message: str = None,
    duration: float = 0,
):

    try:

        steps = audit_steps_context.get()

        step_order = len(steps) + 1

        steps.append(
            {
                "step_name": name,
                "step_order": step_order,
                "status": status,
                "message": message,
                "duration_ms": duration,
            }
        )

    except LookupError:

        print(
            f"[{status}] {name}: {message}"
        )
def get_client_ip(request: Request) -> str:
    # 1. Buscar en los headers puros del scope de la petición
    # ASGI guarda los headers como una lista de tuplas de bytes: [(b"host", b"localhost"), (b"x-forwarded-for", b"192.168.1.50")]
    headers = dict(request.scope.get("headers", []))
    
    # Intentar obtener x-forwarded-for en bytes
    x_forwarded_for = headers.get(b"x-forwarded-for")
    if x_forwarded_for:
        # Decodificar el byte a string y procesarlo
        ip_string = x_forwarded_for.decode("utf-8")
        return ip_string.split(",")[0].strip()
        
    # Intentar obtener x-real-ip en bytes
    x_real_ip = headers.get(b"x-real-ip")
    if x_real_ip:
        return x_real_ip.decode("utf-8").strip()
        
    # 2. Si no viene de un proxy, usar el cliente directo de FastAPI
    if request.client:
        return request.client.host
        
    return "0.0.0.0"