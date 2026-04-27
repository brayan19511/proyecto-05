
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.security.permission.permission_schemas import AssingnRoleToUserRequest, PermisionCreateRequest
from app.api.security.permission.permission_service import PermissionService
from app.api.security.role.role_service import RoleService
from app.core.db_postgres import get_db


router = APIRouter(    prefix="/permission",    tags=["Permission"],)

@router.post("/assign-role")
def assign_role_to_user(role_request: AssingnRoleToUserRequest, db: Session = Depends(get_db)):
    """
    Assign a role to a user.

    - **user_id**: The ID of the user to whom the role will be assigned.
    - **role_id**: The ID of the role to be assigned.
    """
    role_service = RoleService(db)
    role_service.assign_role_to_user(role_request.user_id, role_request.role_id)
    return {"message": f"Role with ID {role_request.role_id} assigned to user with ID {role_request.user_id}."}

@router.get("/getall")
def get_all_permissions(db: Session = Depends(get_db)):
    """
    Get all permissions.

    """
    permission_service = PermissionService(db)
    permissions = permission_service.get_all_permissions()
    return {"permissions": permissions}

@router.post("/register")
def create_permission(permission_request: PermisionCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new permission.

    - **permission_code**: The code of the permission to be created. sap.read, cic.execute
    - **permission_description**: The description of the permission to be created. sap.read: Permiso para leer datos de SAP, cic.execute: Permiso para ejecutar procesos en CIC
    """
    permission_service = PermissionService(db)
    new_permission = permission_service.create_permission(permission_request)
    return {"message": f"Permission with code {new_permission.code} created successfully.", "permission_id": new_permission.id}