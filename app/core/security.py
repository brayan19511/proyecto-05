"""Password, JWT, and permission helpers for interactive users."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.api.security.auth.auth_repository import AuthRepository
from app.core.config import settings
from app.core.db.db_postgres import get_db


pwd_context = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/security/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, minutes: int | None = None) -> str:
    payload = data.copy()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=minutes or settings.JWT_EXPIRES_MIN
    )
    payload.update({"exp": expires_at})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


def get_user_from_token(
    token: str,
    db: Session,
    request: Request | None = None,
):
    """Resolve a JWT when a route supports more than one auth mechanism."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        subject = decode_token(token).get("sub")
        if subject is None:
            raise credentials_error
        user_id = UUID(subject)
    except Exception:
        raise credentials_error

    user = AuthRepository(db).get_by_id(user_id)
    if user is None:
        raise credentials_error
    if not user.active:
        raise HTTPException(status_code=403, detail="Usuario inactivo.")

    if request is not None:
        request.state.user_id = user.id
        request.state.auth_type = "jwt"
    return user


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    return get_user_from_token(token=token, db=db, request=request)


class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user=Depends(get_current_user)):
        roles = {role.name for role in current_user.active_roles}
        if "Admin" in roles:
            return current_user

        permissions = {permission.code for permission in current_user.permissions}
        if self.required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "No tienes el permiso necesario: "
                    f"{self.required_permission}"
                ),
            )
        return current_user
