# app/api/security/permission/permission_service.py
from sqlalchemy.orm import Session
from app.api.security.role.role_repository import RoleRepository
from app.api.security.permission.permission_repository import PermissionRepository
from app.api.security.permission.permission_schemas import PermisionCreateRequest

class PermissionService:
    def __init__(self, db: Session):
        self.permission_repository = PermissionRepository(db)   
        self.role_repository = RoleRepository(db)
    def get_all_permissions(self):
        # Aquí iría la lógica para obtener todos los permisos de la base de datos
        return self.permission_repository.get_all_permissions()
    def create_permission(self, new_permission:PermisionCreateRequest):
        # Aquí iría la lógica para crear un permiso en la base de datos
        return self.permission_repository.create_permission(new_permission)
    def get_permission(self, permission_id: int):
        # Aquí iría la lógica para obtener un permiso por su ID
        return self.permission_repository.get_permission_by_id(permission_id)
    def get_permission_by_code(self, code: str):
        # Aquí iría la lógica para obtener un permiso por su código
        return self.permission_repository.get_permission_by_code(code)
    def delete_permission(self, permission_id: int):
        # Aquí iría la lógica para eliminar un permiso
        return self.permission_repository.delete_permission(permission_id)  
    
    def assign_role_to_permission(self, role_id: int, permission_id: int):
        # validar que el permiso exista
        permission = self.permission_repository.get_permission_by_id(permission_id)
        if not permission:
            raise ValueError(f"Permission with ID {permission_id} does not exist.")
        # validar que el permiso esté activo        if not permission.active:
        if not permission.active:
            raise ValueError(f"Permission with ID {permission_id} is not active.")
        #validar que el rol exista
        # Aquí iría la lógica para validar que el rol exista, similar a como se valida
        role= self.role_repository.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} does not exist.")
        if not role.active:
            raise ValueError(f"Role with ID {role_id} is not active.")
        # Aquí iría la lógica para asignar un rol a un permiso
        self.permission_repository.assign_role_to_permission(role_id, permission_id)