from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.security.permission.permission_schemas import PermisionResponse
from app.api.security.role.role_schemas import (
    AssingnRoleToUserRequest,
    RoleRequest,
    RoleResponse,
)
from app.api.security.role.role_service import RoleService
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.core.security import PermissionChecker


router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleResponse])
async def get_roles(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_any_permission("security.roles.view", "security.roles.edit"),
    ),
):
    role_service = RoleService(db)
    return role_service.get_all_roles()


@router.post("/register")
async def create_role(
    data: RoleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    role_service = RoleService(db)
    return role_service.create_role(data)


@router.post("/assign-role")
async def assign_role_to_user(
    role_request: AssingnRoleToUserRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    role_service = RoleService(db)

    try:
        return role_service.assign_role_to_user(role_request.user_id, role_request.role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/assign-role")
async def remove_role_from_user(
    role_request: AssingnRoleToUserRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    role_service = RoleService(db)

    try:
        return role_service.remove_role_from_user(
            role_request.user_id,
            role_request.role_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{role_id}")
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_any_permission("security.roles.view", "security.roles.edit"),
    ),
):
    role_service = RoleService(db)
    role = role_service.get_role(role_id)

    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")

    return role


@router.get("/{role_id}/permissions", response_model=list[PermisionResponse])
async def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_any_permission("security.roles.view", "security.roles.edit"),
    ),
):
    role_service = RoleService(db)

    try:
        return role_service.get_role_permissions(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    data: RoleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    role_service = RoleService(db)

    try:
        return role_service.update_role(role_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(PermissionChecker("security.roles.edit")),
):
    role_service = RoleService(db)

    try:
        return role_service.delete_role(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
