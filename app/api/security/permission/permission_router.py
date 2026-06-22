from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.security.permission.permission_schemas import (
    AssignRoleToPermissionRequest,
    PermisionCreateRequest,
    PermisionResponse,
    PermissionUpdateRequest,
)
from app.api.security.permission.permission_service import PermissionService
from app.core.db.db_postgres import get_db
from app.core.security import PermissionChecker, get_current_user


router = APIRouter(prefix="/permission", tags=["Permission"])


def require_roles_view(current_user=Depends(get_current_user)):
    role_names = {
        link.role.name
        for link in current_user.user_roles_links
        if link.active
    }
    permission_codes = {permission.code for permission in current_user.permissions}

    if "Admin" in role_names or permission_codes.intersection(
        {"security.roles.view", "security.roles.edit"}
    ):
        return current_user

    raise HTTPException(status_code=403, detail="No tienes permisos para ver permisos")


@router.get("/getall", response_model=dict[str, list[PermisionResponse]])
def get_all_permissions(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_view),
):
    permission_service = PermissionService(db)
    return {"permissions": permission_service.get_all_permissions()}


@router.post("/register")
def create_permission(
    permission_request: PermisionCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    try:
        permission_service = PermissionService(db)
        new_permission = permission_service.create_permission(permission_request)
        return {
            "message": f"Permission with code {new_permission.code} created successfully.",
            "permission_id": new_permission.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assign-role")
def assign_role_to_permission(
    role_request: AssignRoleToPermissionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    try:
        permission_service = PermissionService(db)
        return permission_service.assign_role_to_permission(
            role_request.role_id,
            role_request.permission_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/assign-role")
def remove_role_permission(
    role_request: AssignRoleToPermissionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    try:
        permission_service = PermissionService(db)
        return permission_service.remove_role_permission(
            role_request.role_id,
            role_request.permission_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{permission_id}", response_model=PermisionResponse)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles_view),
):
    try:
        permission_service = PermissionService(db)
        return permission_service.get_permission(permission_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{permission_id}", response_model=PermisionResponse)
def update_permission(
    permission_id: int,
    permission_request: PermissionUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    try:
        permission_service = PermissionService(db)
        return permission_service.update_permission(permission_id, permission_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{permission_id}")
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    try:
        permission_service = PermissionService(db)
        return permission_service.delete_permission(permission_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
