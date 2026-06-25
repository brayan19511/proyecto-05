# app/api/security/role/role_service.py
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.security.auth.auth_repository import AuthRepository
from app.api.security.role.role_repository import RoleRepository
from app.api.security.role.role_schemas import RoleRequest
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError

class RoleService:
    def __init__(self,db:Session):
        self.role_repository = RoleRepository(db)  
        self.auth_repository = AuthRepository(db)  
        
    def get_all_roles(self):
        return self.role_repository.get_all_roles()
    def get_role_by_name(self, name):
        return self.role_repository.get_role_by_name(name)
    def create_role(self, role_data: RoleRequest):
        name = role_data.name.strip()
        if self.role_repository.get_role_by_name(name):
            raise ConflictError("Ya existe un rol con este nombre")

        try:
            return self.role_repository.create_role(
                RoleRequest(name=name, active=role_data.active)
            )
        except IntegrityError as exc:
            self.role_repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={"uq_role_name": "Ya existe un rol con este nombre"},
            )

    def get_role(self, role_id):
        return self.role_repository.get_role_by_id(role_id)

    def get_role_permissions(self, role_id: int):
        role = self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found.")

        return role.permissions

    def update_role(self, role_id, role_data: RoleRequest):
        role=self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found.")
        name = role_data.name.strip()
        existing = self.role_repository.get_role_by_name(name)
        if existing and existing.id != role_id:
            raise ConflictError("Ya existe un rol con este nombre")

        try:
            result = self.role_repository.update_role(
                role,
                RoleRequest(name=name, active=role_data.active),
            )
        except IntegrityError as exc:
            self.role_repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={"uq_role_name": "Ya existe un rol con este nombre"},
            )
        if not result:
            raise ValueError(f"Failed to update role with ID {role_id}.")
        return {"message": "Role updated successfully"}

    def delete_role(self, role_id):
        role=self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found.")
        
        result= self.role_repository.delete_role(role)
        if not result:
            raise ValueError(f"Failed to delete role with ID {role_id}.")
        return {"message": "Role deleted successfully"}
        
    def assign_role_to_user(self, user_id: UUID, role_id: int):
        # validate role
        role=self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} does not exist.")
        if not role.active:
            raise ValueError(f"Role with ID {role_id} is not active.")
        
        # validate user 
        user=self.auth_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist.")
        user_role = self.role_repository.get_user_role(user_id, role_id)

        if user_role:
            if user_role.active:
                return {
                    "assigned": False,
                    "already_exists": True,
                    "message": "El usuario ya tiene este rol activo",
                }

            self.role_repository.activate_user_role(user_role)
            return {
                "assigned": True,
                "reactivated": True,
                "message": "Rol reactivado correctamente",
            }

        try:
            self.role_repository.assign_role_to_user(user_id, role_id)
        except IntegrityError:
            self.role_repository.rollback()
            return {
                "assigned": False,
                "already_exists": True,
                "message": "El usuario ya tiene este rol",
            }
        return {
            "assigned": True,
            "message": "Rol asignado correctamente",
        }

    def remove_role_from_user(self, user_id: UUID, role_id: int):
        removed = self.role_repository.deactivate_user_role(user_id, role_id)

        if not removed:
            raise ValueError("El usuario no tiene este rol asignado.")

        return {"message": "Rol removido correctamente"}
