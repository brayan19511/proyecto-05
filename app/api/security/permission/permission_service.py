from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.security.permission.permission_repository import PermissionRepository
from app.api.security.permission.permission_schemas import (
    PermisionCreateRequest,
    PermissionUpdateRequest,
)
from app.api.security.role.role_repository import RoleRepository
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError


class PermissionService:
    def __init__(self, db: Session):
        self.permission_repository = PermissionRepository(db)
        self.role_repository = RoleRepository(db)

    def get_all_permissions(self):
        return self.permission_repository.get_all_permissions()

    def create_permission(self, new_permission: PermisionCreateRequest):
        code = new_permission.code.strip().lower()
        if self.permission_repository.get_permission_by_code(code):
            raise ConflictError(f"El permiso '{code}' ya existe")

        try:
            return self.permission_repository.create_permission(
                PermisionCreateRequest(
                    code=code,
                    description=new_permission.description.strip(),
                )
            )
        except IntegrityError as exc:
            self.permission_repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={"uq_permission_code": f"El permiso '{code}' ya existe"},
            )

    def get_permission(self, permission_id: int):
        permission = self.permission_repository.get_permission_by_id(permission_id)

        if not permission:
            raise ValueError(f"Permission with ID {permission_id} does not exist.")

        return permission

    def get_permission_by_code(self, code: str):
        return self.permission_repository.get_permission_by_code(code)

    def update_permission(
        self,
        permission_id: int,
        permission_data: PermissionUpdateRequest,
    ):
        permission = self.get_permission(permission_id)
        data = permission_data.model_dump(exclude_unset=True)

        if "code" in data:
            data["code"] = data["code"].strip().lower()
            existing = self.permission_repository.get_permission_by_code(data["code"])
            if existing and existing.id != permission_id:
                raise ConflictError(f"El permiso '{data['code']}' ya existe")

        try:
            return self.permission_repository.update_permission(
                permission,
                PermissionUpdateRequest(**data),
            )
        except IntegrityError as exc:
            self.permission_repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={
                    "uq_permission_code": (
                        f"El permiso '{data.get('code', permission.code)}' ya existe"
                    )
                },
            )

    def delete_permission(self, permission_id: int):
        if not self.permission_repository.delete_permission(permission_id):
            raise ValueError(f"Permission with ID {permission_id} does not exist.")

        return {"message": "Permiso desactivado correctamente"}

    def assign_role_to_permission(self, role_id: int, permission_id: int):
        role = self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} does not exist.")
        if not role.active:
            raise ValueError(f"Role with ID {role_id} is not active.")

        permission = self.permission_repository.get_permission_by_id(permission_id)
        if not permission:
            raise ValueError(f"Permission with ID {permission_id} does not exist.")
        if not permission.active:
            raise ValueError(f"Permission with ID {permission_id} is not active.")

        role_permission = self.permission_repository.get_role_permission(
            role_id,
            permission_id,
        )
        if role_permission:
            return {
                "assigned": False,
                "already_exists": True,
                "message": "El rol ya tiene este permiso",
            }

        try:
            self.permission_repository.assign_role_to_permission(
                role_id,
                permission_id,
            )
        except IntegrityError:
            self.permission_repository.rollback()
            return {
                "assigned": False,
                "already_exists": True,
                "message": "El rol ya tiene este permiso",
            }
        return {
            "assigned": True,
            "message": "Permiso asignado correctamente",
        }

    def remove_role_permission(self, role_id: int, permission_id: int):
        role = self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} does not exist.")

        permission = self.permission_repository.get_permission_by_id(permission_id)
        if not permission:
            raise ValueError(f"Permission with ID {permission_id} does not exist.")

        if not self.permission_repository.remove_role_permission(role_id, permission_id):
            raise ValueError("El rol no tiene este permiso asignado.")

        return {"message": "Permiso removido del rol correctamente"}
