

from sqlalchemy.orm import Session

from app.api.role.role_repository import RoleRepository
from app.api.role.role_schemas import RoleRequest


class RoleService:
    def __init__(self,db:Session):
        self.role_repository = RoleRepository(db)  # Assume db is available here
    def get_all_roles(self):
        return self.role_repository.get_all_roles()
    def create_role(self, role_data: RoleRequest):
        return self.role_repository.create_role(role_data)

    def get_role(self, role_id):
        return self.role_repository.get_role_by_id(role_id)

    def update_role(self, role_id, role_data: RoleRequest):
        return self.role_repository.update_role(role_id, role_data)

    def delete_role(self, role_id):
        
        if self.role_repository.delete_role(role_id):
            return {"message": "Role deactivated successfully"}
        return {"message": "Role not found"}