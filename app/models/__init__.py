# app/models/__init__.py
from app.core.db.db_postgres import Base # Importas tu Base
from .analytics import AnalyticsIngestionItem, AnalyticsIngestionRun
from .auth import Auth, Role, UserRole, Information, Permission, RolePermission
from .audit import AuditLog, AuditLogDetail, AuditStep
from .finance import Provision, ProvisionAccess, ProvisionConcept, ProvisionDocument, ProvisionStatus
from .finance import LibroMayor, ReglasGastos
from .finance import PaymentProvider
from .master import Area, Company, Currency, MailingParameter
from .jobs import Job, JobBatch, JobItem, ScheduledJob
from .storage import Attachment
from .tickets import Tickets
# Esto asegura que ambas clases estén disponibles en el Registry de SQLAlchemy
__all__ = [
    "Base", 
    "AnalyticsIngestionItem", "AnalyticsIngestionRun",
    "Auth", "Role", "UserRole", "Information",
    "AuditLog", "AuditLogDetail", "AuditStep", "Permission", "RolePermission" , 
    "Provision", "ProvisionAccess", "ProvisionConcept", "ProvisionDocument", "ProvisionStatus",
    "Company", "Currency", "Area", "MailingParameter", "Attachment",
    "Job", "JobBatch", "JobItem", "ScheduledJob",
    "LibroMayor", "ReglasGastos",
    "PaymentProvider",
    "Tickets"
    ]
