import logging
from collections.abc import Mapping

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ValidationError


logger = logging.getLogger(__name__)


def get_constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(exc.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def raise_integrity_error(
    exc: IntegrityError,
    *,
    conflicts: Mapping[str, str] | None = None,
    invalid_references: Mapping[str, str] | None = None,
    default_message: str = "No se pudo guardar la informacion",
) -> None:
    constraint_name = get_constraint_name(exc)

    if conflicts and constraint_name in conflicts:
        raise ConflictError(conflicts[constraint_name]) from exc

    if invalid_references and constraint_name in invalid_references:
        raise ValidationError(invalid_references[constraint_name]) from exc

    logger.error(
        "Unhandled database integrity error constraint=%s",
        constraint_name,
        exc_info=exc,
    )
    raise ValidationError(default_message) from exc
