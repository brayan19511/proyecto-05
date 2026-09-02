# app/core/exceptions.py
from typing import TypeVar


class DomainError(Exception):
    pass

class NotFoundError(DomainError):
    pass

class ValidationError(DomainError):
    pass

class ConflictError(DomainError):
    pass

class ForbiddenError(DomainError):
    pass

class BusinessException(DomainError):
    pass

class ModuleDisabledError(DomainError):
    """El modulo funcional esta apagado. handlers lo traduce a 503."""

    def __init__(self, message: str, *, code: str, reason: str):
        self.code = code
        self.reason = reason

        super().__init__(message)

class SAPError(Exception):
    pass

class SAPAuthenticationError(SAPError):
    pass

class SAPConnectionError(SAPError):
    pass

class SAPRequestError(SAPError):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail

        super().__init__(f"SAP Error {status_code}")


T = TypeVar("T")


def get_or_404(entity: T | None, message: str) -> T:
    """Devuelve la entidad o lanza NotFoundError (que handlers traduce a 404)."""
    if entity is None:
        raise NotFoundError(message)
    return entity
