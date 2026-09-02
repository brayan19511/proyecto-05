# app/api/verify/seed_service.py
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.api.attendance.permissions import ATTENDANCE_MARKS_VIEW_PERMISSION
from app.api.graphql.permissions import ICG_QUERY_VIEW_PERMISSION
from app.api.jobs.constants import (
    ANALYTICS_INGEST_RUN_PERMISSION,
    ANALYTICS_INGEST_VIEW_PERMISSION,
    JOBS_CANCEL_ALL_PERMISSION,
    JOBS_CANCEL_PERMISSION,
    JOBS_RETRY_PERMISSION,
    JOBS_VIEW_ALL_PERMISSION,
    JOBS_VIEW_PERMISSION,
    JobType,
    SCHEDULED_JOBS_EDIT_PERMISSION,
    SCHEDULED_JOBS_RUN_PERMISSION,
    SCHEDULED_JOBS_VIEW_PERMISSION,
    ScheduledJobScheduleKind,
)
from app.api.observability.constants import OBSERVABILITY_VIEW_PERMISSION
from app.api.scheduled_jobs.schedule import calculate_next_run
from app.api.finance.provisions.constants import (
    APPROVED_STATUS,
    CANCELLED_STATUS,
    PENDING_DETAIL_STATUS,
    READY_FOR_REVIEW_STATUS,
    REJECTED_FINAL_STATUS,
    REJECTED_FOR_EDIT_STATUS,
)
from app.api.finance.payment_provider.constants import (
    DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER,
)
from app.api.sales_channel.permissions import (
    PROMOTION_EDIT_PERMISSION,
    PROMOTION_IMPORT_PERMISSION,
    PROMOTION_VIEW_PERMISSION,
    SKU_EDIT_PERMISSION,
    SKU_IMPORT_PERMISSION,
    SKU_VIEW_PERMISSION,
)
from app.core.modules import MODULE_CATALOG
from app.core.security import hash_password
from app.models.auth.security_model import (
    Auth,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.models.auth.user_model import Information
from app.models.finance.provision_model import ProvisionStatus
from app.models.jobs import ScheduledJob
from app.models.master.mailing_parameter_model import MailingParameter
from app.models.master.master_model import Area, Company, Currency, Module
from app.services.ingestion.catalog import ICG_TABLES

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin123"

COMPANIES = [
    {
        "code": "RASH",
        "name": "RASH PERU SRL",
        "rut": "20378890161",
    },
]

AREAS = [
    {
        "code": "CON",
        "name": "Contabilidad",
        "description": "Area de contabilidad",
    },
    {
        "code": "FIN",
        "name": "Finanzas",
        "description": "Area de finanzas",
    },
    {
        "code": "TI",
        "name": "TI",
        "description": "Area de tecnologia",
    },
]

CURRENCIES = [
    {
        "code": "PEN",
        "name": "Sol Peruano",
        "symbol": "S/",
        "exchange_rate_to_base": 1,
        "is_base_currency": True,
    },
    {
        "code": "USD",
        "name": "Dolar Americano",
        "symbol": "$",
        "exchange_rate_to_base": 3.75,
        "is_base_currency": False,
    },
    {
        "code": "EUR",
        "name": "Euro",
        "symbol": "EUR",
        "exchange_rate_to_base": 4.05,
        "is_base_currency": False,
    },
]

# Cada flujo debe tener un unico parametro por defecto para evitar aliases
# silenciosos y facilitar que el frontend sepa que configuracion esta usando.
MAILING_PARAMETERS = [
    {
        "name": DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER,
        "template": "payment_provider_summary.html",
        "template_html": None,
        "template_text": None,
        "mp_from": "Coolbox <no-reply@coolbox.com.pe>",
        "to": None,
        "subject": "CONSTANCIA DE PAGO {{ proveedor }} || RASH PERU",
        "cc": None,
        "bcc": None,
    },
]

PERMISSIONS = [
    {"code": "sap.read", "description": "Ver datos de SAP"},
    {"code": "sap.write", "description": "Modificar datos en SAP"},
    {"code": "sap.execute", "description": "Ejecutar operaciones en SAP"},
    {"code": "security.roles.view", "description": "Ver roles y permisos"},
    {"code": "security.roles.edit", "description": "Editar roles y permisos"},
    {"code": "security.users.view", "description": "Ver usuarios y perfiles"},
    {"code": "security.users.edit", "description": "Editar usuarios y perfiles"},
    {"code": "cic.execute", "description": "Ejecutar procesos automaticos CIC"},
    {"code": "master.company.view", "description": "Ver empresas"},
    {"code": "master.company.edit", "description": "Gestionar empresas"},
    {"code": "master.currency.view", "description": "Ver monedas"},
    {"code": "master.currency.edit", "description": "Gestionar monedas"},
    {"code": "master.area.view", "description": "Ver areas"},
    {"code": "master.area.edit", "description": "Gestionar areas"},
    {"code": "master.data.view", "description": "Ver datos maestros generales"},
    {"code": "master.data.edit", "description": "Editar datos maestros"},
    {"code": "provisions.create", "description": "Crear provisiones"},
    {"code": "provisions.submit", "description": "Enviar provisiones a revision"},
    {"code": "provisions.review", "description": "Revisar y aprobar provisiones"},
    {"code": "provisions.cancel", "description": "Cancelar provisiones"},
    {"code": "provisions.view_all", "description": "Ver todas las provisiones"},
    {"code": "provisions.edit_all", "description": "Editar todas las provisiones"},
    {"code": "provisions.concepts.view", "description": "Ver conceptos de provisiones"},
    {
        "code": "provisions.concepts.edit",
        "description": "Gestionar conceptos de provisiones",
    },
    {
        "code": "provisions.documents.view",
        "description": "Ver documentos de provisiones",
    },
    {
        "code": "provisions.documents.edit",
        "description": "Gestionar documentos de provisiones",
    },
    {
        "code": "provisions.access.edit",
        "description": "Gestionar accesos de provisiones",
    },
    {"code": "provisions.view", "description": "Ver provisiones"},
    {"code": "provisions.edit", "description": "Gestionar provisiones"},
    {"code": "expenses.view", "description": "Ver gastos"},
    {"code": "expenses.create", "description": "Crear gastos"},
    {"code": "expenses.edit", "description": "Gestionar gastos"},
    {"code": "expenses.review", "description": "Revisar gastos"},
    {"code": "expenses.view_all", "description": "Ver todos los gastos"},
    {"code": "expenses.edit_all", "description": "Editar todos los gastos"},
    {"code": "payment_provider.view", "description": "Ver pagos a proveedores"},
    {
        "code": "payment_provider.process",
        "description": "Procesar PDFs de pagos a proveedores",
    },
    {
        "code": "payment_provider.edit",
        "description": "Gestionar proveedores y parametros de correo",
    },
    {"code": "ledger.view", "description": "Ver libro mayor"},
    {"code": "ledger.export", "description": "Exportar libro mayor"},
    {"code": "ledger.sync", "description": "Sincronizar libro mayor"},
    {
        "code": SKU_VIEW_PERMISSION,
        "description": "Ver SKU de canales de venta",
    },
    {
        "code": SKU_EDIT_PERMISSION,
        "description": "Gestionar SKU de canales de venta",
    },
    {
        "code": SKU_IMPORT_PERMISSION,
        "description": "Importar y sincronizar SKU de canales de venta",
    },
    {
        "code": PROMOTION_VIEW_PERMISSION,
        "description": "Ver promociones de canales de venta",
    },
    {
        "code": PROMOTION_EDIT_PERMISSION,
        "description": "Gestionar promociones de canales de venta",
    },
    {
        "code": PROMOTION_IMPORT_PERMISSION,
        "description": "Importar promociones de canales de venta",
    },
    {
        "code": ATTENDANCE_MARKS_VIEW_PERMISSION,
        "description": "Ver registros de asistencia",
    },
    {"code": JOBS_VIEW_PERMISSION, "description": "Ver tareas propias"},
    {
        "code": JOBS_VIEW_ALL_PERMISSION,
        "description": "Ver tareas de todos los usuarios",
    },
    {"code": JOBS_CANCEL_PERMISSION, "description": "Cancelar tareas propias"},
    {
        "code": JOBS_CANCEL_ALL_PERMISSION,
        "description": "Cancelar tareas de todos los usuarios",
    },
    {"code": JOBS_RETRY_PERMISSION, "description": "Reintentar tareas"},
    {
        "code": SCHEDULED_JOBS_VIEW_PERMISSION,
        "description": "Ver tareas programadas",
    },
    {
        "code": SCHEDULED_JOBS_EDIT_PERMISSION,
        "description": "Gestionar tareas programadas",
    },
    {
        "code": SCHEDULED_JOBS_RUN_PERMISSION,
        "description": "Ejecutar tareas programadas manualmente",
    },
    {
        "code": ANALYTICS_INGEST_VIEW_PERMISSION,
        "description": "Ver catalogo y ejecuciones analytics",
    },
    {
        "code": ANALYTICS_INGEST_RUN_PERMISSION,
        "description": "Ejecutar ingestas analytics",
    },
    {
        "code": OBSERVABILITY_VIEW_PERMISSION,
        "description": "Ver estado del sistema y analitica de logs/jobs",
    },
    {
        "code": ICG_QUERY_VIEW_PERMISSION,
        "description": "Consultar datos de ICG por GraphQL",
    },
    {
        "code": "master.modules.view",
        "description": "Ver el estado de los modulos del sistema",
    },
    {
        "code": "master.modules.edit",
        "description": "Activar y desactivar modulos del sistema",
    },
]

ROLES = [
    "Admin",
    "Admin SAP",
    "Master Consulta",
    "Master Admin",
    "Contabilidad Consulta",
    "Contabilidad",
    "Contabilidad Admin",
    "Gastos Consulta",
    "Gastos Operador",
    "Gastos Admin",
    "Pagos Proveedores Consulta",
    "Pagos Proveedores Operador",
    "Pagos Proveedores Admin",
    "Canales Venta Consulta",
    "Canales Venta Importador",
    "Canales Venta Admin",
    "Asistencia Consulta",
    "Tareas Consulta",
    "Tareas Operador",
    "Tareas Admin",
    "Analytics Operador",
    "Observabilidad",
]

ROLE_PERMISSIONS = {
    "Admin SAP": {
        "ledger.view",
        "ledger.export",
        "ledger.sync",
        "sap.read",
        "sap.write",
        "sap.execute",
        JOBS_VIEW_PERMISSION,
        JOBS_VIEW_ALL_PERMISSION,
        JOBS_CANCEL_PERMISSION,
        JOBS_CANCEL_ALL_PERMISSION,
        JOBS_RETRY_PERMISSION,
    },
    "Master Consulta": {
        "master.modules.view",
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "master.data.view",
    },
    "Master Admin": {
        "master.modules.view",
        "master.modules.edit",
        "master.company.view",
        "master.company.edit",
        "master.currency.view",
        "master.currency.edit",
        "master.area.view",
        "master.area.edit",
        "master.data.view",
        "master.data.edit",
    },
    "Contabilidad Consulta": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "provisions.view",
        "provisions.concepts.view",
        "provisions.documents.view",
    },
    "Contabilidad": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "provisions.create",
        "provisions.submit",
        "provisions.view",
        "provisions.edit",
        "provisions.concepts.view",
        "provisions.documents.view",
        "provisions.documents.edit",
    },
    "Contabilidad Admin": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "master.area.edit",
        "provisions.create",
        "provisions.submit",
        "provisions.view",
        "provisions.view_all",
        "provisions.edit",
        "provisions.edit_all",
        "provisions.review",
        "provisions.cancel",
        "provisions.concepts.view",
        "provisions.concepts.edit",
        "provisions.documents.view",
        "provisions.documents.edit",
        "provisions.access.edit",
        "master.data.edit",
    },
    "Gastos Consulta": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "expenses.view",
    },
    "Gastos Operador": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "expenses.view",
        "expenses.create",
        "expenses.edit",
    },
    "Gastos Admin": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
        "expenses.view",
        "expenses.view_all",
        "expenses.create",
        "expenses.edit",
        "expenses.edit_all",
        "expenses.review",
    },
    "Pagos Proveedores Consulta": {
        "payment_provider.view",
        JOBS_VIEW_PERMISSION,
    },
    "Pagos Proveedores Operador": {
        "payment_provider.view",
        "payment_provider.process",
        JOBS_VIEW_PERMISSION,
        JOBS_CANCEL_PERMISSION,
    },
    "Pagos Proveedores Admin": {
        "payment_provider.view",
        "payment_provider.process",
        "payment_provider.edit",
        JOBS_VIEW_PERMISSION,
        JOBS_VIEW_ALL_PERMISSION,
        JOBS_CANCEL_PERMISSION,
        JOBS_CANCEL_ALL_PERMISSION,
        JOBS_RETRY_PERMISSION,
        SCHEDULED_JOBS_VIEW_PERMISSION,
        SCHEDULED_JOBS_EDIT_PERMISSION,
        SCHEDULED_JOBS_RUN_PERMISSION,
    },
    "Canales Venta Consulta": {
        SKU_VIEW_PERMISSION,
        PROMOTION_VIEW_PERMISSION,
    },
    "Canales Venta Importador": {
        SKU_VIEW_PERMISSION,
        SKU_IMPORT_PERMISSION,
        PROMOTION_VIEW_PERMISSION,
        PROMOTION_IMPORT_PERMISSION,
    },
    "Canales Venta Admin": {
        SKU_VIEW_PERMISSION,
        SKU_EDIT_PERMISSION,
        SKU_IMPORT_PERMISSION,
        PROMOTION_VIEW_PERMISSION,
        PROMOTION_EDIT_PERMISSION,
        PROMOTION_IMPORT_PERMISSION,
    },
    "Asistencia Consulta": {
        ATTENDANCE_MARKS_VIEW_PERMISSION,
    },
    "Tareas Consulta": {
        JOBS_VIEW_PERMISSION,
    },
    "Tareas Operador": {
        JOBS_VIEW_PERMISSION,
        JOBS_CANCEL_PERMISSION,
    },
    "Tareas Admin": {
        JOBS_VIEW_PERMISSION,
        JOBS_VIEW_ALL_PERMISSION,
        JOBS_CANCEL_PERMISSION,
        JOBS_CANCEL_ALL_PERMISSION,
        JOBS_RETRY_PERMISSION,
        SCHEDULED_JOBS_VIEW_PERMISSION,
        SCHEDULED_JOBS_EDIT_PERMISSION,
        SCHEDULED_JOBS_RUN_PERMISSION,
    },
    "Analytics Operador": {
        ANALYTICS_INGEST_VIEW_PERMISSION,
        ANALYTICS_INGEST_RUN_PERMISSION,
        JOBS_VIEW_PERMISSION,
        JOBS_CANCEL_PERMISSION,
    },
    "Observabilidad": {
        OBSERVABILITY_VIEW_PERMISSION,
        JOBS_VIEW_ALL_PERMISSION,
        SCHEDULED_JOBS_VIEW_PERMISSION,
    },
}

PROVISION_STATUSES = [
    {"code": "DRAFT", "name": "Borrador"},
    {"code": PENDING_DETAIL_STATUS, "name": "Pendiente de completar detalle"},
    {"code": READY_FOR_REVIEW_STATUS, "name": "Listo para revision"},
    {"code": "REVIEWING", "name": "En revision"},
    {"code": APPROVED_STATUS, "name": "Aprobado"},
    {"code": REJECTED_FOR_EDIT_STATUS, "name": "Observado para corregir"},
    {"code": REJECTED_FINAL_STATUS, "name": "Rechazado definitivo"},
    {"code": CANCELLED_STATUS, "name": "Cancelado"},
    {"code": "POSTED_SAP", "name": "Registrado en SAP"},
    {"code": "SAP_ERROR", "name": "Error SAP"},
]

DEFAULT_SCHEDULED_JOBS = [
    {
        "name": "Libro mayor delta laboral",
        "job_type": JobType.LEDGER_SYNC_DELTA.value,
        "enabled": True,
        "schedule_kind": ScheduledJobScheduleKind.WINDOW_INTERVAL.value,
        "schedule_config": {
            "weekdays": [0, 1, 2, 3, 4],
            "start_time": "08:00",
            "end_time": "18:00",
            "minutes": 240,
        },
        "parameters": {"operation": "sync_delta_all"},
        "batch_size": 1,
        "timezone": "America/Lima",
    },
]


ICG_TRANSACTIONAL_RECOVERY_TIME = "08:00"
ICG_TRANSACTIONAL_CURRENT_DAY_TIMES = ["12:00", "16:00"]
ICG_MASTER_LOAD_TIME = "07:00"


def build_default_icg_scheduled_jobs() -> list[dict]:
    return [
        {
            "name": "ICG transaccional incremental recuperacion",
            "job_type": JobType.ANALYTICS_EXTRACT.value,
            "enabled": True,
            "schedule_kind": ScheduledJobScheduleKind.DAILY.value,
            "schedule_config": {"times": [ICG_TRANSACTIONAL_RECOVERY_TIME]},
            "parameters": {
                "table_group": "transactional",
                "mode": "incremental",
                "lookback_days": 3,
            },
            "batch_size": 1,
            "timezone": "America/Lima",
        },
        {
            "name": "ICG transaccional incremental dia actual",
            "job_type": JobType.ANALYTICS_EXTRACT.value,
            "enabled": True,
            "schedule_kind": ScheduledJobScheduleKind.DAILY.value,
            "schedule_config": {"times": ICG_TRANSACTIONAL_CURRENT_DAY_TIMES},
            "parameters": {
                "table_group": "transactional",
                "mode": "incremental",
                "lookback_days": 0,
            },
            "batch_size": 1,
            "timezone": "America/Lima",
        },
        {
            "name": "ICG maestros snapshot diario",
            "job_type": JobType.ANALYTICS_EXTRACT.value,
            "enabled": True,
            "schedule_kind": ScheduledJobScheduleKind.DAILY.value,
            "schedule_config": {"times": [ICG_MASTER_LOAD_TIME]},
            "parameters": {
                "table_group": "master",
                "mode": "snapshot",
            },
            "batch_size": 1,
            "timezone": "America/Lima",
        },
    ]


DEFAULT_SCHEDULED_JOBS.extend(build_default_icg_scheduled_jobs())


class SeedService:
    def __init__(self, db: Session):
        self.db = db
        self.created = []
        self.existing = []

    def run_seed(self):
        try:
            permissions = self.ensure_permissions()
            roles = self.ensure_roles()
            admin_user = self.ensure_admin_user()

            self.ensure_role_permissions(roles["Admin"], permissions.values())
            self.ensure_functional_role_permissions(roles, permissions)
            self.ensure_user_role(admin_user, roles["Admin"])
            self.ensure_user_profile(admin_user)
            self.ensure_master_data()
            self.ensure_mailing_parameters()
            self.ensure_provision_statuses()
            self.ensure_scheduled_jobs(admin_user)
            self.disable_legacy_icg_scheduled_jobs()

            self.db.commit()

            return {
                "status": "success",
                "message": "Seed verificado correctamente",
                "created": self.created,
                "existing": self.existing,
            }

        except Exception:
            self.db.rollback()
            raise

    # =====================================================
    # SECURITY
    # =====================================================
    def ensure_permissions(self):
        permissions = {}

        for item in PERMISSIONS:
            permission = (
                self.db.query(Permission)
                .filter(Permission.code == item["code"])
                .first()
            )

            if permission:
                permission.description = item["description"]
                permission.active = True
                self.existing.append(f"permission:{item['code']}")
            else:
                permission = Permission(
                    code=item["code"],
                    description=item["description"],
                    active=True,
                )
                self.db.add(permission)
                self.db.flush()
                self.created.append(f"permission:{item['code']}")

            permissions[item["code"]] = permission

        return permissions

    def ensure_roles(self):
        roles = {}

        for role_name in ROLES:
            role = self.db.query(Role).filter(Role.name == role_name).first()

            if role:
                role.active = True
                self.existing.append(f"role:{role_name}")
            else:
                role = Role(
                    name=role_name,
                    active=True,
                )
                self.db.add(role)
                self.db.flush()
                self.created.append(f"role:{role_name}")

            roles[role_name] = role

        return roles

    def ensure_admin_user(self):
        admin_user = self.db.query(Auth).filter(Auth.email == ADMIN_EMAIL).first()

        if admin_user:
            admin_user.active = True
            self.existing.append(f"user:{ADMIN_EMAIL}")
            return admin_user

        admin_user = Auth(
            id=uuid7(),
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            active=True,
        )
        self.db.add(admin_user)
        self.db.flush()
        self.created.append(f"user:{ADMIN_EMAIL}")

        return admin_user

    def ensure_user_profile(self, user: Auth):
        profile = (
            self.db.query(Information).filter(Information.user_id == user.id).first()
        )

        if profile:
            self.existing.append(f"user_profile:{user.email}")
            return profile

        profile = Information(user_id=user.id)
        self.db.add(profile)
        self.created.append(f"user_profile:{user.email}")
        return profile

    def ensure_role_permissions(self, role: Role, permissions):
        for permission in permissions:
            exists = (
                self.db.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
                .first()
            )

            if exists:
                self.existing.append(f"role_permission:{role.name}:{permission.code}")
                continue

            self.db.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )
            self.created.append(f"role_permission:{role.name}:{permission.code}")

    def ensure_functional_role_permissions(self, roles: dict, permissions: dict):
        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            role = roles[role_name]
            role_permissions = [
                permissions[permission_code]
                for permission_code in permission_codes
                if permission_code in permissions
            ]

            self.ensure_role_permissions(role, role_permissions)

    def ensure_user_role(self, user: Auth, role: Role):
        user_role = (
            self.db.query(UserRole)
            .filter(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
            .first()
        )

        if user_role:
            user_role.active = True
            self.existing.append(f"user_role:{user.email}:{role.name}")
            return

        self.db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                active=True,
            )
        )
        self.created.append(f"user_role:{user.email}:{role.name}")

    # =====================================================
    # MASTER
    # =====================================================
    def ensure_master_data(self):
        for item in COMPANIES:
            self.ensure_company(item)

        for item in AREAS:
            self.ensure_area(item)

        for item in CURRENCIES:
            self.ensure_currency(item)

        self.ensure_modules()

    def ensure_modules(self):
        """Siembra el catalogo de modulos sin tocar el estado ya elegido.

        Solo se actualizan nombre y descripcion: si el operador apago un
        modulo, volver a correr el seed no lo debe prender.
        """
        for item in MODULE_CATALOG:
            module = (
                self.db.query(Module)
                .filter(Module.code == item["code"])
                .first()
            )

            if module:
                module.name = item["name"]
                module.description = item["description"]
                self.existing.append(f"module:{item['code']}")
                continue

            self.db.add(
                Module(
                    code=item["code"],
                    name=item["name"],
                    description=item["description"],
                    enabled=True,
                )
            )
            self.created.append(f"module:{item['code']}")

    def ensure_mailing_parameters(self):
        for item in MAILING_PARAMETERS:
            parameter = (
                self.db.query(MailingParameter)
                .filter(MailingParameter.name == item["name"])
                .first()
            )

            if parameter:
                # Se actualiza solo la base funcional; los destinatarios por
                # proveedor se toman de PaymentProvider.emails_payments.
                parameter.template = item["template"]
                parameter.template_html = item["template_html"]
                parameter.template_text = item["template_text"]
                parameter.mp_from = item["mp_from"]
                parameter.subject = item["subject"]
                parameter.active = True
                self.existing.append(f"mailing_parameter:{item['name']}")
                continue

            self.db.add(MailingParameter(**item, active=True))
            self.created.append(f"mailing_parameter:{item['name']}")

    def ensure_company(self, item: dict):
        company = self.db.query(Company).filter(Company.code == item["code"]).first()

        if company:
            company.name = item["name"]
            company.rut = item["rut"]
            company.active = True
            self.existing.append(f"company:{item['code']}")
            return company

        company = Company(**item, active=True)
        self.db.add(company)
        self.created.append(f"company:{item['code']}")
        return company

    def ensure_area(self, item: dict):
        area = self.db.query(Area).filter(Area.code == item["code"]).first()

        if area:
            area.name = item["name"]
            area.description = item["description"]
            area.active = True
            self.existing.append(f"area:{item['code']}")
            return area

        area = Area(**item, active=True)
        self.db.add(area)
        self.created.append(f"area:{item['code']}")
        return area

    def ensure_currency(self, item: dict):
        currency = self.db.query(Currency).filter(Currency.code == item["code"]).first()

        if currency:
            currency.name = item["name"]
            currency.symbol = item["symbol"]
            currency.exchange_rate_to_base = item["exchange_rate_to_base"]
            currency.is_base_currency = item["is_base_currency"]
            currency.active = True
            self.existing.append(f"currency:{item['code']}")
            return currency

        currency = Currency(**item, active=True)
        self.db.add(currency)
        self.created.append(f"currency:{item['code']}")
        return currency

    # =====================================================
    # PROVISIONS
    # =====================================================
    def ensure_provision_statuses(self):
        for item in PROVISION_STATUSES:
            status = (
                self.db.query(ProvisionStatus)
                .filter(ProvisionStatus.code == item["code"])
                .first()
            )

            if status:
                status.name = item["name"]
                self.existing.append(f"provision_status:{item['code']}")
                continue

            self.db.add(
                ProvisionStatus(
                    code=item["code"],
                    name=item["name"],
                )
            )
            self.created.append(f"provision_status:{item['code']}")

    # =====================================================
    # SCHEDULED JOBS
    # =====================================================
    def ensure_scheduled_jobs(self, admin_user: Auth):
        for item in DEFAULT_SCHEDULED_JOBS:
            scheduled_job = (
                self.db.query(ScheduledJob)
                .filter(ScheduledJob.name == item["name"])
                .first()
            )
            next_run_at = calculate_next_run(
                schedule_kind=item["schedule_kind"],
                schedule_config=item["schedule_config"],
                tz_name=item["timezone"],
            )

            if scheduled_job:
                # El seed mantiene la definicion base, pero no borra historial
                # ni el ultimo job asociado a esta programacion.
                scheduled_job.job_type = item["job_type"]
                scheduled_job.enabled = item["enabled"]
                scheduled_job.schedule_kind = item["schedule_kind"]
                scheduled_job.schedule_config = item["schedule_config"]
                scheduled_job.parameters = item["parameters"]
                scheduled_job.batch_size = item["batch_size"]
                scheduled_job.timezone = item["timezone"]
                if not scheduled_job.next_run_at:
                    scheduled_job.next_run_at = next_run_at
                self.existing.append(f"scheduled_job:{item['name']}")
                continue

            self.db.add(
                ScheduledJob(
                    **item,
                    next_run_at=next_run_at,
                    created_by=admin_user.id,
                )
            )
            self.created.append(f"scheduled_job:{item['name']}")

    def disable_legacy_icg_scheduled_jobs(self):
        grouped_names = {item["name"] for item in build_default_icg_scheduled_jobs()}
        legacy_names = set()
        for table in ICG_TABLES.values():
            legacy_names.update(
                {
                    f"ICG {table.name} incremental recuperacion",
                    f"ICG {table.name} incremental dia actual",
                    f"ICG {table.name} snapshot diario",
                }
            )

        for scheduled_job in (
            self.db.query(ScheduledJob)
            .filter(ScheduledJob.name.in_(legacy_names - grouped_names))
            .all()
        ):
            if scheduled_job.enabled:
                scheduled_job.enabled = False
                self.existing.append(f"scheduled_job_disabled:{scheduled_job.name}")
