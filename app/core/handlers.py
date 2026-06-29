"""Application-level exception to HTTP response mappings."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import NotFoundError, ValidationError


logger = logging.getLogger(__name__)


def register_exception_handlers(app) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", None)
        logger.exception("Unhandled request error. trace_id=%s", trace_id)

        # Internal details stay in logs and are correlated through trace_id.
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Error interno del servidor",
                "trace_id": trace_id,
            },
        )
