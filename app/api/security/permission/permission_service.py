from sqlalchemy.orm import Session
from app.api.security.permission.permission_repository import PermissionRepository
from app.api.security.permission.permission_schemas import PermisionCreateRequest

class PermissionService:
    def __init__(self, db: Session):
        self.permission_repository = PermissionRepository(db)   
    def get_all_permissions(self):
        # Aquí iría la lógica para obtener todos los permisos de la base de datos
        return self.permission_repository.get_all_permissions()
    def create_permission(self, new_permission:PermisionCreateRequest):
        # Aquí iría la lógica para crear un permiso en la base de datos
        return self.permission_repository.create_permission(new_permission)
    def get_permission(self, permission_id: int):
        # Aquí iría la lógica para obtener un permiso por su ID
        return self.permission_repository.get_permission_by_id(permission_id)
    def delete_permission(self, permission_id: int):
        # Aquí iría la lógica para eliminar un permiso
        return self.permission_repository.delete_permission(permission_id)  