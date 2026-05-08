
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.security.permission.permission_schemas import AssignRoleToPermissionRequest, PermisionCreateRequest
from app.api.security.permission.permission_service import PermissionService
from app.api.security.role.role_service import RoleService
from app.core.db_postgres import get_db


router = APIRouter(    prefix="/permission",    tags=["Permission"],)

@router.post("/assign-role")
def assign_role_to_permission(role_request: AssignRoleToPermissionRequest, db: Session = Depends(get_db)):
    """
    Assign a role to a permission.

    - **permission_id**: The ID of the permission to which the role will be assigned.
    - **role_id**: The ID of the role to be assigned.
    """
    try:
        # validate role and permission existence and active status
        permission_service = PermissionService(db)
        permission_service.assign_role_to_permission(role_request.role_id, role_request.permission_id)
        return {"message": f"Role with ID {role_request.role_id} assigned to permission with ID {role_request.permission_id}."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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