# app/core/exceptions.py
class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class BusinessException(DomainError):
    pass

