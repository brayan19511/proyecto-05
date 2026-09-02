# app/models/auth/__init__.py
from .security_model import (
    Auth,
    Role,
    UserRole,
    Permission,
    RolePermission,
    UserAreaAccess,
)
from .user_model import Information
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = [
    "Auth",
    "Role",
    "UserRole",
    "Information",
    "Permission",
    "RolePermission",
    "UserAreaAccess",
]