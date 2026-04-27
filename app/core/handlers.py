from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)


def register_exception_handlers(app):
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", None)

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Error interno del servidor",
                "trace_id": trace_id,
            },
        )
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", None)
        # con ub if debug DEBUG = os.getenv("ENV", "dev") == "dev"
        # if DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "trace_id": trace_id,
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Error interno del servidor",
                "trace_id": trace_id,
            },
        )