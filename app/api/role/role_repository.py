


from sqlalchemy.orm import Session

from app.api.role.role_schemas import RoleRequest
from app.models.security import Role


class RoleRepository:
    def __init__(self, db:Session):
        self.db = db

    def get_role_by_id(self, role_id:int):
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_all_roles(self):
        return self.db.query(Role).all()

    def create_role(self, role:RoleRequest):
        new_role = Role(name=role.name, system_name=role.system_name)
        self.db.add(new_role)
        self.db.commit()
        self.db.refresh(new_role)
        return new_role

    def delete_role(self, role_id):
        role = self.get_role_by_id(role_id)
        if role:
            role.active = False
            self.db.commit()
            return True
        return False
    def update_role(self, role_id:int, role_data:RoleRequest):
        role = self.get_role_by_id(role_id)
        if role:
            role.name = role_data.name
            role.system_name = role_data.system_name
            self.db.commit()
            self.db.refresh(role)
            return role
        return None
    