# app/models/audit/__init__.py
from .audit_model import AuditLog,AuditLogDetail,AuditStep
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = ["AuditLog", "AuditLogDetail", "AuditStep"]