from contextvars import ContextVar
import logging
from typing import Any

from starlette.requests import Request


logger = logging.getLogger(__name__)
audit_steps_context: ContextVar[list[dict[str, Any]]] = ContextVar(
    "audit_steps_context"
)


async def get_request_body(request: Request):
    body = await request.body()

    async def receive():
        return {
            "type": "http.request",
            "body": body,
        }

    request._receive = receive
    return body


def add_step(
    name: str,
    status: str = "INFO",
    message: str | None = None,
    duration: float = 0,
):
    try:
        steps = audit_steps_context.get()
        steps.append(
            {
                "step_name": name,
                "step_order": len(steps) + 1,
                "status": status,
                "message": message,
                "duration_ms": duration,
            }
        )
    except LookupError:
        logger.warning(
            "Audit step outside request context: status=%s name=%s message=%s",
            status,
            name,
            message,
        )


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "0.0.0.0"
