"""Idempotent bootstrap of roles, permissions, and the initial administrator."""

from uuid6 import uuid7

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.verify.seed_definitions import PERMISSIONS, ROLE_PERMISSIONS, ROLES
from app.core.config import settings
from app.core.security import hash_password
from app.models import Auth, Permission, Role, RolePermission, UserRole


class SeedService:
    """Reconcile the minimum security catalog in one transaction."""

    def __init__(self, db: Session):
        self.db = db

    def run_seed(self) -> dict:
        # A concurrent seed may win a unique-key race. Retrying after rollback
        # turns that situation into the same idempotent reconciliation.
        for attempt in range(2):
            try:
                result = self._reconcile()
                self.db.commit()
                return {"status": "success", **result}
            except IntegrityError:
                self.db.rollback()
                if attempt == 1:
                    raise
            except Exception:
                self.db.rollback()
                raise

        raise RuntimeError("No se pudo completar el seed.")

    def _reconcile(self) -> dict:
        counters = {
            "created": 0,
            "updated": 0,
            "existing": 0,
            "relations_created": 0,
        }

        permissions = {
            code: self._ensure_permission(code, description, counters)
            for code, description in PERMISSIONS
        }
        roles = {
            name: self._ensure_role(name, counters)
            for name in ROLES
        }

        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            for code in permission_codes:
                self._ensure_role_permission(
                    roles[role_name],
                    permissions[code],
                    counters,
                )

        admin_result = self._ensure_admin(roles["Admin"], counters)

        return {
            "message": "Datos base verificados correctamente.",
            "summary": counters,
            "admin": admin_result,
        }

    def _ensure_permission(
        self,
        code: str,
        description: str,
        counters: dict,
    ) -> Permission:
        permission = self.db.scalar(
            select(Permission).where(Permission.code == code)
        )

        if permission is None:
            permission = Permission(
                code=code,
                description=description,
                active=True,
            )
            self.db.add(permission)
            self.db.flush()
            counters["created"] += 1
            return permission

        changed = permission.description != description or not permission.active
        permission.description = description
        permission.active = True
        counters["updated" if changed else "existing"] += 1
        return permission

    def _ensure_role(self, name: str, counters: dict) -> Role:
        role = self.db.scalar(select(Role).where(Role.name == name))

        if role is None:
            role = Role(name=name, active=True)
            self.db.add(role)
            self.db.flush()
            counters["created"] += 1
            return role

        if not role.active:
            role.active = True
            counters["updated"] += 1
        else:
            counters["existing"] += 1
        return role

    def _ensure_role_permission(
        self,
        role: Role,
        permission: Permission,
        counters: dict,
    ) -> None:
        relation = self.db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if relation is None:
            self.db.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )
            counters["relations_created"] += 1

    def _ensure_admin(self, admin_role: Role, counters: dict) -> dict:
        email = settings.SEED_ADMIN_EMAIL
        password = settings.SEED_ADMIN_PASSWORD

        if not email:
            return {
                "status": "skipped",
                "detail": "SEED_ADMIN_EMAIL no esta configurado.",
            }

        admin = self.db.scalar(select(Auth).where(Auth.email == email))
        if admin is None:
            if not password:
                return {
                    "status": "skipped",
                    "detail": (
                        "El usuario no existe y SEED_ADMIN_PASSWORD "
                        "no esta configurado."
                    ),
                }
            admin = Auth(
                id=uuid7(),
                email=email,
                password_hash=hash_password(password),
                active=True,
            )
            self.db.add(admin)
            self.db.flush()
            counters["created"] += 1
            admin_status = "created"
        else:
            if not admin.active:
                admin.active = True
                counters["updated"] += 1
                admin_status = "reactivated"
            else:
                counters["existing"] += 1
                admin_status = "existing"

        relation = self.db.scalar(
            select(UserRole).where(
                UserRole.user_id == admin.id,
                UserRole.role_id == admin_role.id,
            )
        )
        if relation is None:
            self.db.add(
                UserRole(
                    user_id=admin.id,
                    role_id=admin_role.id,
                    active=True,
                )
            )
            counters["relations_created"] += 1
        elif not relation.active:
            relation.active = True
            counters["updated"] += 1

        return {"status": admin_status, "email": email}
