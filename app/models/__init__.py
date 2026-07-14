# app/models/__init__.py
from app.core.db.db_postgres import Base # Importas tu Base
from .auth import Auth, Role, UserRole, Information, Permission, RolePermission
from .audit import AuditLog, AuditLogDetail, AuditStep
from .finance import Provision, ProvisionAccess, ProvisionConcept, ProvisionDocument, ProvisionStatus
from .finance import LibroMayor, ReglasGastos
from .finance import PaymentProvider
from .master import Area, Company, Currency, MailingParameter
from .jobs import Job, JobBatch, JobItem
from .storage import Attachment
from .tickets import Tickets
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = [
    "Base", 
    "Auth", "Role", "UserRole", "Information",
    "AuditLog", "AuditLogDetail", "AuditStep", "Permission", "RolePermission" , 
    "Provision", "ProvisionAccess", "ProvisionConcept", "ProvisionDocument", "ProvisionStatus",
    "Company", "Currency", "Area", "MailingParameter", "Attachment",
    "Job", "JobBatch", "JobItem",
    "LibroMayor", "ReglasGastos",
    "PaymentProvider",
    "Tickets"
    ]
