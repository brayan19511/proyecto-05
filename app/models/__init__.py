"""Central model registry used by Alembic and repositories."""

from app.core.db.db_postgres import Base

from .audit import AuditLog, AuditLogDetail, AuditStep
from .auth import (
    ApiClient,
    Auth,
    Information,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from .coolbox.ventas.coolbox_ventas_model import Ventas

__all__ = [
    "Base",
    "ApiClient",
    "Auth",
    "Role",
    "UserRole",
    "Information",
    "Permission",
    "RolePermission",
    "Ventas",
    "AuditLog",
    "AuditLogDetail",
    "AuditStep",
]
