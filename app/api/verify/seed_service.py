# app/api/verify/seed_service.py
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.security import hash_password
from app.models.auth.security_model import (
    Auth,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.models.finance.provision_model import ProvisionStatus
from app.models.master.master_model import Area, Company, Currency


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
    {"code": "master.data.edit", "description": "Editar datos maestros"},
    {"code": "provisions.create", "description": "Crear provisiones"},
    {"code": "provisions.submit", "description": "Enviar provisiones a revision"},
    {"code": "provisions.review", "description": "Revisar y aprobar provisiones"},
    {"code": "provisions.cancel", "description": "Cancelar provisiones"},
    {"code": "provisions.view_all", "description": "Ver todas las provisiones"},
    {"code": "provisions.edit_all", "description": "Editar todas las provisiones"},
    {"code": "provisions.concepts.view", "description": "Ver conceptos de provisiones"},
    {"code": "provisions.concepts.edit", "description": "Gestionar conceptos de provisiones"},
    {"code": "provisions.documents.view", "description": "Ver documentos de provisiones"},
    {"code": "provisions.documents.edit", "description": "Gestionar documentos de provisiones"},
    {"code": "provisions.access.edit", "description": "Gestionar accesos de provisiones"},
    {"code": "provisions.view", "description": "Ver provisiones"},
    {"code": "provisions.edit", "description": "Gestionar provisiones"},
    {"code": "expenses.view", "description": "Ver gastos"},
    {"code": "expenses.create", "description": "Crear gastos"},
    {"code": "expenses.edit", "description": "Gestionar gastos"},
    {"code": "expenses.review", "description": "Revisar gastos"},
    {"code": "expenses.view_all", "description": "Ver todos los gastos"},
    {"code": "expenses.edit_all", "description": "Editar todos los gastos"},
    {"code": "ledger.view", "description": "Ver libro mayor"},
    {"code": "ledger.export", "description": "Exportar libro mayor"},
    {"code": "ledger.sync", "description": "Sincronizar libro mayor"},
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
]

ROLE_PERMISSIONS = {
    "Admin SAP": {
        "ledger.view",
        "ledger.export",
        "ledger.sync",
        "sap.read",
        "sap.write",
        "sap.execute",
    },
    "Master Consulta": {
        "master.company.view",
        "master.currency.view",
        "master.area.view",
    },
    "Master Admin": {
        "master.company.view",
        "master.company.edit",
        "master.currency.view",
        "master.currency.edit",
        "master.area.view",
        "master.area.edit",
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
}

PROVISION_STATUSES = [
    {"code": "DRAFT", "name": "Borrador"},
    {"code": "PENDING_DETAIL", "name": "Pendiente de completar detalle"},
    {"code": "READY_FOR_REVIEW", "name": "Listo para revision"},
    {"code": "REVIEWING", "name": "En revision"},
    {"code": "APPROVED", "name": "Aprobado"},
    {"code": "REJECTED_FOR_EDIT", "name": "Observado para corregir"},
    {"code": "REJECTED_FINAL", "name": "Rechazado definitivo"},
    {"code": "CANCELLED", "name": "Cancelado"},
    {"code": "POSTED_SAP", "name": "Registrado en SAP"},
    {"code": "SAP_ERROR", "name": "Error SAP"},
]


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
            self.ensure_master_data()
            self.ensure_provision_statuses()

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
            role = (
                self.db.query(Role)
                .filter(Role.name == role_name)
                .first()
            )

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
        admin_user = (
            self.db.query(Auth)
            .filter(Auth.email == ADMIN_EMAIL)
            .first()
        )

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

    def ensure_company(self, item: dict):
        company = (
            self.db.query(Company)
            .filter(Company.code == item["code"])
            .first()
        )

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
        area = (
            self.db.query(Area)
            .filter(Area.code == item["code"])
            .first()
        )

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
        currency = (
            self.db.query(Currency)
            .filter(Currency.code == item["code"])
            .first()
        )

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
