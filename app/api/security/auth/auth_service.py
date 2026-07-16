import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from uuid6 import uuid7

from app.api.security.auth.auth_repository import AuthRepository
from app.api.security.auth.auth_schemas import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    TokenResponse,
    UserRegisterSchema,
    UserTokenResponse,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError
from app.models import Auth, Information


logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db):
        self.auth_repository = AuthRepository(db)

    def authenticate_user(self, login_data: LoginRequest) -> TokenResponse:
        user = self.auth_repository.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contrasena incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo",
            )

        token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
            }
        )
        return TokenResponse(
            access_token=token,
            user=UserTokenResponse(
                user_id=user.id,
                email=user.email,
                roles=[
                    link.role.name
                    for link in user.user_roles_links
                    if link.active
                ],
            ),
        )

    def get_by_email(self, email: str):
        return self.auth_repository.get_by_email(email)

    def change_my_password(self, user, request: PasswordChangeRequest):
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contrasena actual no es correcta",
            )

        user.password_hash = hash_password(request.new_password)
        self.auth_repository.commit()
        return {"message": "Contrasena actualizada"}

    def reset_user_password(self, user_id, request: PasswordResetRequest):
        user = self.auth_repository.get_by_id(str(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        user.password_hash = hash_password(request.new_password)
        self.auth_repository.commit()
        return {"message": "Contrasena restablecida"}

    def register_user(self, data: UserRegisterSchema):
        email = data.email.strip().lower()
        if self.auth_repository.get_by_email(email):
            raise ConflictError("Email ya registrado")

        try:
            user_id = uuid7()
            new_auth = Auth(
                id=user_id,
                email=email,
                password_hash=hash_password(data.password),
            )
            self.auth_repository.create_auth(new_auth)
            self.auth_repository.create_information(Information(user_id=user_id))
            self.auth_repository.commit()
            return {
                "message": "Usuario creado exitosamente",
                "id": user_id,
            }
        except IntegrityError as exc:
            self.auth_repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={"auth_email_key": "Email ya registrado"},
                default_message="No se pudo crear el usuario",
            )
        except Exception as exc:
            self.auth_repository.rollback()
            logger.exception("Error al crear usuario")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo crear el usuario",
            ) from exc
