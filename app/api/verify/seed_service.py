# app/api/security/seed/seed_service.py
from sqlalchemy.orm import Session
from app.api.security.auth.auth_schemas import UserRegisterSchema
from app.api.security.role.role_service import RoleService
from app.api.security.auth.auth_service import AuthService
from app.api.security.permission.permission_service import PermissionService
from app.api.security.role.role_schemas import RoleRequest
from app.api.security.permission.permission_schemas import PermisionCreateRequest

class SeedService:
    def __init__(self, db: Session):
        self.db = db
        self.role_service = RoleService(db)
        self.auth_service = AuthService(db)
        self.perm_service = PermissionService(db)
        
    def run_seed(self):
        # 1. DEFINIR PERMISOS (Granulares)
        perms_data = [
            # Módulo SAP
            {"code": "sap.read", "desc": "Ver datos de SAP"},
            {"code": "sap.write", "desc": "Modificar datos en SAP"},
            # Módulo Seguridad (Para que los admins puedan gestionar el sistema)
            {"code": "security.roles.edit", "desc": "Editar roles y sus permisos"},
            {"code": "security.users.view", "desc": "Ver lista de usuarios y sus perfiles"},
            # Otros módulos
            {"code": "cic.execute", "desc": "Ejecutar procesos automáticos CIC"},
        ]
        
        perms_objects = {}
        for p in perms_data:
            # Buscamos si existe (necesitas implementar get_permission_by_code en tu service)
            existing_p = self.perm_service.get_permission_by_code(p["code"])
            if not existing_p:
                existing_p = self.perm_service.create_permission(
                    PermisionCreateRequest(code=p["code"], description=p["desc"])
                )
            perms_objects[p["code"]] = existing_p

        # 2. DEFINIR ROLES
        roles_to_create = ["Admin", "Admin SAP"]
        roles_objects = {}
        for role_name in roles_to_create:
            existing_r = self.role_service.get_role_by_name(role_name) # Implementar este método
            if not existing_r:
                existing_r = self.role_service.create_role(
                    RoleRequest(name=role_name, active=True)
                )
            roles_objects[role_name] = existing_r

        # 3. ASIGNAR PERMISOS A ROLES
        # Admin recibe todo
        admin_role = roles_objects["Admin"]
        for p_obj in perms_objects.values():
            # Debes validar en tu service que no se duplique en la tabla intermedia
            self.perm_service.assign_role_to_permission(admin_role.id, p_obj.id)

        # 4. CREAR USUARIO ADMIN INICIAL
        admin_email = "admin@admin.com"
        # Supongamos que tu AuthService ya maneja la verificación de "si existe"
        admin_user = self.auth_service.get_by_email(admin_email)
        
        if not admin_user:
            admin_user = self.auth_service.register_user(UserRegisterSchema(email=admin_email, password="admin123"))
            # Asignar rol
            self.role_service.assign_role_to_user(admin_user["id"], admin_role.id)

        return {"status": "success", "message": "Seeding completed"}