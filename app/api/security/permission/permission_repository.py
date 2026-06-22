from sqlalchemy.orm import Session

from app.api.security.permission.permission_schemas import (
    PermisionCreateRequest,
    PermissionUpdateRequest,
)
from app.models import Permission, RolePermission


class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_permissions(self):
        return self.db.query(Permission).all()

    def create_permission(self, req: PermisionCreateRequest):
        if self.get_permission_by_code(req.code):
            raise ValueError(f"Permission with code '{req.code}' already exists.")

        permission = Permission(
            code=req.code,
            description=req.description,
        )
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def get_permission_by_id(self, permission_id: int):
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    def get_permission_by_code(self, code: str):
        return self.db.query(Permission).filter(Permission.code == code).first()

    def update_permission(
        self,
        permission: Permission,
        req: PermissionUpdateRequest,
    ):
        data = req.model_dump(exclude_unset=True)

        for field, value in data.items():
            setattr(permission, field, value)

        self.db.commit()
        self.db.refresh(permission)
        return permission

    def delete_permission(self, permission_id: int):
        permission = self.get_permission_by_id(permission_id)

        if not permission:
            return False

        permission.active = False
        self.db.commit()
        return True

    def get_role_permission(self, role_id: int, permission_id: int):
        return (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            .first()
        )

    def assign_role_to_permission(self, role_id: int, permission_id: int):
        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
        )
        self.db.add(role_permission)
        self.db.commit()
        return role_permission

    def remove_role_permission(self, role_id: int, permission_id: int):
        role_permission = self.get_role_permission(role_id, permission_id)

        if not role_permission:
            return False

        self.db.delete(role_permission)
        self.db.commit()
        return True
