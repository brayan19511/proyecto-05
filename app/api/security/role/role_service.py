# app/api/security/role/role_service.py
from sqlalchemy.orm import Session

from app.api.security.auth.auth_repository import AuthRepository
from app.api.security.role.role_repository import RoleRepository
from app.api.security.role.role_schemas import RoleRequest

class RoleService:
    def __init__(self,db:Session):
        self.role_repository = RoleRepository(db)  
        self.auth_repository = AuthRepository(db)  
        
    def get_all_roles(self):
        return self.role_repository.get_all_roles()
    def get_role_by_name(self, name):
        return self.role_repository.get_role_by_name(name)
    def create_role(self, role_data: RoleRequest):
        return self.role_repository.create_role(role_data)

    def get_role(self, role_id):
        return self.role_repository.get_role_by_id(role_id)

    def update_role(self, role_id, role_data: RoleRequest):
        role=self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found.")
        result =self.role_repository.update_role(role, role_data)
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
        
    def assign_role_to_user(self, user_id: int, role_id: int):
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
        #validate if role is already assigned to user
        if self.role_repository.is_role_assigned_to_user(user_id, role_id):
            raise ValueError(f"User with ID {user_id} already has role with ID {role_id}.") 
        self.role_repository.assign_role_to_user(user_id, role_id)
        