# app/models/__init__.py
from app.core.db_postgres import Base # Importas tu Base
from .auth import Auth, Role, UserRole, Information, Permission, RolePermission
from .audit import AuditLog, AuditLogDetail, AuditStep
from .finance import Provision, ProvisionConcept, ProvisionDocument, ProvisionStatus
from .master import Currency, Area, Attachment
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = [
    "Base", 
    "Auth", "Role", "UserRole", "Information",
    "AuditLog", "AuditLogDetail", "AuditStep", "Permission", "RolePermission" , 
    "Provision", "ProvisionConcept", "ProvisionDocument", "ProvisionStatus", "Currency", "Area", "Attachment"
    ]