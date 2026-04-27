


from sqlalchemy.orm import Session

from app.api.security.role.role_schemas import RoleRequest
from app.models.security import Role, UserRole



class RoleRepository:
    def __init__(self, db:Session):
        self.db = db

    def get_role_by_id(self, role_id:int):
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_all_roles(self):
        return self.db.query(Role).all()

    def create_role(self, role:RoleRequest):
        new_role = Role(name=role.name, active=role.active)
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
            role.active = role_data.active
            self.db.commit()
            self.db.refresh(role)
            return role
        return None
    def assign_role_to_user(self, user_id: int, role_id: int):
        role = self.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found.")
        
        user_role = UserRole(user_id=user_id, role_id=role.id)
        self.db.add(user_role)
        self.db.commit()