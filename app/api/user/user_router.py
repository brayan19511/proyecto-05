# app/api/user/user_router.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.user import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
    UserService,
)
from app.core.db.db_postgres import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def get_role_names(current_user) -> set[str]:
    return {
        link.role.name
        for link in current_user.user_roles_links
        if link.active
    }


def get_permission_codes(current_user) -> set[str]:
    return {permission.code for permission in current_user.permissions}


def can_view_users(current_user) -> bool:
    roles = get_role_names(current_user)
    permissions = get_permission_codes(current_user)

    return (
        "Admin" in roles
        or "security.roles.edit" in permissions
        or "security.users.view" in permissions
        or "security.users.edit" in permissions
    )


def can_edit_users(current_user) -> bool:
    roles = {
        link.role.name
        for link in current_user.user_roles_links
        if link.active
    }
    permissions = {permission.code for permission in current_user.permissions}

    return (
        "Admin" in roles
        or "security.roles.edit" in permissions
        or "security.users.edit" in permissions
    )


def ensure_self_or_user_admin(
    user_id: UUID,
    current_user,
    *,
    write: bool = False,
):
    if user_id == current_user.id:
        return

    if write and can_edit_users(current_user):
        return

    if not write and can_view_users(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para acceder a este usuario",
    )


@router.get("/getall", response_model=list[UserProfileResponse])
async def get_users(
    search: str | None = Query(default=None),
    email: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not can_view_users(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para listar usuarios",
        )

    user_service = UserService(db)
    return user_service.get_users(
        search=search,
        email=email,
        active=active,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_service = UserService(db)
    return user_service.get_user_profile(current_user.id)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    user_update: UserProfileUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_service = UserService(db)
    return user_service.update_profile(current_user.id, user_update)


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_self_or_user_admin(user_id, current_user)

    user_service = UserService(db)
    return user_service.get_user_profile(user_id)


@router.post("/{user_id}", response_model=UserProfileResponse)
async def create_user(
    user_id: UUID,
    user_create: UserProfileCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_self_or_user_admin(user_id, current_user, write=True)

    user_service = UserService(db)
    return user_service.create_user_profile(user_id, user_create)


@router.patch("/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: UUID,
    user_update: UserProfileUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_self_or_user_admin(user_id, current_user, write=True)

    user_service = UserService(db)
    return user_service.update_profile(user_id, user_update)
