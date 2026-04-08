# app/api/auth/auth_router.py
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session
from app.api.auth.auth_repository import AuthRepository
from app.core.db_postgres import get_db
from app.core.security import get_current_user
from app.models.security import Auth
from .auth_schemas import LoginRequest, PasswordChangeRequest, TokenResponse, UserRegisterSchema
from .auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.authenticate_user(login_data)
@router.post("/register")
def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register_user(user_data)
@router.post("/change-password")
def change_password(
    data: PasswordChangeRequest, 
    db: Session = Depends(get_db),
    current_user: Auth = Depends(get_current_user) # Tu futura dependencia de seguridad
):
    service = AuthService(db)
    return service.change_user_password(current_user.id, data)
@router.post("/assign-role/{user_id}/{role_id}")
def assign_role(
    user_id: UUID, 
    role_id: int, 
    db: Session = Depends(get_db),
    # Aquí deberías validar que el current_user sea ADMIN
    admin_user: Auth = Depends(get_current_user) 
):
    # Lógica: Buscar user, buscar role, y asociar
    auth_service = AuthService(db)
    return auth_service.update_role_to_user(user_id, role_id, status=True)
@router.post("/activate-role/{user_id}/{role_id}")
def deactivate_role(
    user_id: UUID, 
    role_id: int, 
    db: Session = Depends(get_db),
    # Aquí deberías validar que el current_user sea ADMIN
    admin_user: Auth = Depends(get_current_user) 
):
    # Lógica: Buscar user, buscar role, y asociar
    auth_service = AuthService(db)
    return auth_service.update_role_to_user(user_id, role_id, status=False)

@router.post("/deactivate-user/{user_id}")
def deactivate_user(
    user_id: UUID, 
    db: Session = Depends(get_db),
    admin_user: Auth = Depends(get_current_user) # Validar ADMIN
):
    auth_service = AuthService(db)
    return auth_service.update_Status_user(user_id,False)
@router.post("/activate-user/{user_id}")
def activate_user(
    user_id: UUID, 
    db: Session = Depends(get_db),
    admin_user: Auth = Depends(get_current_user) # Validar ADMIN
):
    auth_service = AuthService(db)
    return auth_service.update_Status_user(user_id,True)