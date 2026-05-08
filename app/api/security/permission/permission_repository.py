# app/api/security/permission/permission_repository.py

from sqlalchemy.orm import Session

from app.api.security.permission.permission_schemas import PermisionCreateRequest
from app.models.security import Permission, RolePermission

class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db
    def get_all_permissions(self):
        # Lógica para obtener todos los permisos de la base de datos
        return self.db.query(Permission).all()
    def create_permission(self, req: PermisionCreateRequest):
        # Lógica para crear un nuevo permiso
        if self.get_permission_by_code(req.code):
            raise ValueError(f"Permission with code '{req.code}' already exists.")
        new_permission = Permission(code=req.code, description=req.description)
        self.db.add(new_permission)
        self.db.commit()
        self.db.refresh(new_permission)
        return new_permission
    def get_permission_by_id(self, permission_id: int):
        # Lógica para obtener un permiso por su ID
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    def get_permission_by_code(self, code: str):
        # Lógica para obtener un permiso por su código
        return self.db.query(Permission).filter(Permission.code == code).first()
    def delete_permission(self, permission_id: int):
        # Lógica para eliminar un permiso
        permission = self.get_permission_by_id(permission_id)
        if permission:
            permission.active = False
            self.db.commit()
            return True
        return False
    def assign_role_to_permission(self, role_id: int, permission_id: int):
        # Lógica para asignar un rol a un usuario
        role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        self.db.add(role_permission)
        self.db.commit()
