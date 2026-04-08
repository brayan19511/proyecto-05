

from fastapi import HTTPException,status
from sqlalchemy import UUID
from uuid6 import uuid7

from app.api.auth.auth_repository import AuthRepository
from app.api.auth.auth_schemas import LoginRequest, PasswordChangeRequest, TokenResponse, UserRegisterSchema
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
            # new_info = Information(
            #     user_id=user_id,
            #     name=data.name,
            #     document_type=data.document_type,
            #     document_number=data.document_number
            # )
            # self.authRepository.create_info(new_info)
            self.authRepository.commit()
            return {"message": "Usuario creado exitosamente", "id": user_id}
        except Exception as e:
            self.authRepository.rollback()
            raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")
        
    def change_user_password(self,user_id:UUID,data:PasswordChangeRequest):
        user=self.authRepository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
        new_hashed_password=hash_password(data.new_password)
        if self.authRepository.update_password(user_id, new_hashed_password):
            return {"message": "Contraseña actualizada exitosamente"}
        
    def update_role_to_user(self,user_id:UUID,role_id:int,status:bool):
        user=self.authRepository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        role=self.authRepository.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Rol no encontrado")
        if not role.active:
            raise HTTPException(status_code=400, detail="El rol no está activo")
        self.authRepository.update_role_to_user(user, role, status=status)
        self.authRepository.commit()
        return {"message": f"Rol {role.name} asignado a {user.email} con estado {'activo' if status else 'inactivo'}"}
    def update_Status_user(self, user_id: UUID,status: bool):
        user = self.authRepository.set_user_status(user_id, status=status)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Podrías agregar lógica extra: por ejemplo, invalidar sus tokens actuales
        self.authRepository.commit()
        return {"message": f"Usuario {user.email} { 'activado' if status else 'desactivado' } correctamente"}
    def remove_role_from_user(self, user_id: UUID, role_id: int):
        link = self.authRepository.set_user_role_status(user_id, role_id, status=False)
        
        if not link:
            raise HTTPException(status_code=404, detail="El usuario no tiene asignado ese rol")
        
        self.authRepository.commit()
        return {"message": "Rol desactivado para el usuario con éxito"}