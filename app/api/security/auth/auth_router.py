# app/api/security/auth/auth_router.py
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session
from app.api.security.auth.auth_schemas import *
from app.api.security.auth.auth_service import AuthService
from app.api.security.user_scope.user_scope_service import UserScopeService
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.core.modules import enabled_module_codes
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["AUTENTICACION"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.authenticate_user(login_data)
@router.post("/register")
def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register_user(user_data)
@router.get(
    "/me",
    response_model=CurrentUserResponse
)
def get_me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # El front necesita saber en que empresas / areas puede operar para
    # armar los combos de creacion y los filtros de listado.
    scope = UserScopeService(db).get_user_scope_detail(current_user)

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        active=current_user.active,
        roles=[
            role.role.name
            for role in current_user.user_roles_links
            if role.active
        ],
        permissions=[
            p.code
            for p in current_user.permissions
        ],
        companies=scope.companies,
        unrestricted_scope=scope.unrestricted,
        enabled_modules=enabled_module_codes(db),
    )


@router.post("/me/password")
def change_my_password(
    request: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return auth_service.change_my_password(current_user, request)


@router.post("/users/{user_id}/password-reset")
def reset_user_password(
    user_id: UUID,
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_any_permission("security.users.edit")),
):
    auth_service = AuthService(db)
    return auth_service.reset_user_password(user_id, request)
