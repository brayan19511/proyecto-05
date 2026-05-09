# app/models/__init__.py
from app.core.db_postgres import Base # Importas tu Base
from .security import Auth, Role, UserRole, Permission, RolePermission
from .user import Information
from .audit import AuditLog,AuditLogDetail,AuditStep

# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = ["Base", "Auth", "Role", "UserRole", "Information", "AuditLog", "AuditLogDetail", "AuditStep", "Permission", "RolePermission" ]