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

    forwarded = request.headers.get(
        "x-forwarded-for"
    )

    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get(
        "x-real-ip"
    )

    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "unknown"