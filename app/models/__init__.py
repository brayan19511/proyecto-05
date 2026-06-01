# app/models/__init__.py
from app.core.db.db_postgres import Base # Importas tu Base
from .auth import Auth, Role, UserRole, Information, Permission, RolePermission
from .audit import AuditLog, AuditLogDetail, AuditStep
from .coolbox.ventas.coolbox_ventas_model import Ventas # Importas tu modelo de ventas
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = [
    "Base", 
    "Auth", "Role", "UserRole", "Information", "Permission", "RolePermission" , 
    "Ventas",
    "AuditLog", "AuditLogDetail", "AuditStep"
    ]