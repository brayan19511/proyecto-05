# app/core/audit_utils.py
from starlette.requests import Request

async def get_request_body(request: Request):
    body = await request.body()
    # Re-inyectamos el body para que otros lo puedan leer
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive
    return body
def add_step(request, name: str, status: str = "INFO", message: str = None, duration: float = 0):
    if hasattr(request.state, "audit_steps"):
        step_order = len(request.state.audit_steps) + 1
        request.state.audit_steps.append({
            "step_name": name,
            "step_order": step_order,
            "status": status,
            "message": message,
            "duration_ms": duration
        })