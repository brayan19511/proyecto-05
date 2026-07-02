# app/core/exceptions.py
class DomainError(Exception):
    pass

class NotFoundError(DomainError):
    pass

class ValidationError(DomainError):
    pass

class ConflictError(DomainError):
    pass

class BusinessException(DomainError):
    pass

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
