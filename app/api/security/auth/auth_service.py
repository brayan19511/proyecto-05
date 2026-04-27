# app/api/security/auth/auth_service.py
from fastapi import HTTPException,status
from sqlalchemy import UUID
from uuid6 import uuid7

from app.api.auth.auth_schemas import LoginRequest, PasswordChangeRequest, TokenResponse, UserRegisterSchema
from app.api.security.auth.auth_repository import AuthRepository
from app.core.security import create_access_token, hash_password, verify_password
from app.models.security import Auth
from app.models.user import Information


class AuthService:
    def __init__(self, db):
        self.authRepository = AuthRepository(db)

    def authenticate_user(self, login_data: LoginRequest) -> TokenResponse:
        # 1. Buscar usuario
        user = self.authRepository.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.active:
            raise HTTPException(status_code=403, detail="Usuario inactivo")
        token_data={"sub": str(user.id), "email": user.email}
        token=create_access_token(token_data)
        return TokenResponse(
            access_token=token,
            user_id=user.id
        )
        
    def register_user(self,data:UserRegisterSchema):
        if self.authRepository.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="Email ya registrado")
        try:
            user_id=uuid7()
            hashed_password = hash_password(data.password)
            new_auth=Auth(
                id=user_id,
                email=data.email,
                password_hash=hashed_password
            )
            self.authRepository.create_auth(new_auth)
            self.authRepository.commit()
            return {"message": "Usuario creado exitosamente", "id": user_id}
        except Exception as e:
            self.authRepository.rollback()
            raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")
      