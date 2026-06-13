from datetime import datetime, timedelta
import hashlib

import jwt
from fastapi import (
    Depends,
    HTTPException,
    Header,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.api.security.auth.auth_repository import AuthRepository
from app.core.config import settings
from app.core.db.db_postgres import get_db

pwd_context = PasswordHash.recommended()


# ==========================================================
# PASSWORDS
# ==========================================================


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ==========================================================
# JWT
# ==========================================================


def create_access_token(
    data: dict,
    minutes: int | None = None,
) -> str:
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=minutes or settings.JWT_EXPIRES_MIN)

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALG,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALG],
    )


# ==========================================================
# API KEY
# ==========================================================


def validate_api_key(
    api_key: str,
    db: Session,
):
    from app.api.security.api_key.api_key_repository import (
        ApiKeyRepository,
    )

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    repository = ApiKeyRepository(db)

    key_record = repository.get_by_hash(key_hash)

    if not key_record:
        return None

    if key_record.expires_at and key_record.expires_at < datetime.utcnow():
        return None

    return key_record.user


# ==========================================================
# CURRENT USER
# ==========================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/security/auth/login",
    auto_error=False,
)


def validate_jwt_user(
    token: str,
    db: Session,
):
    try:
        payload = decode_token(token)

        user_id = payload.get("sub")

        if not user_id:
            return None

        repository = AuthRepository(db)

        return repository.get_by_id(user_id)

    except jwt.PyJWTError:
        return None


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
    )

    user = None

    # --------------------------------------
    # JWT
    # --------------------------------------
    if token:
        user = validate_jwt_user(
            token=token,
            db=db,
        )

    # --------------------------------------
    # API KEY
    # --------------------------------------
    if not user and x_api_key:
        user = validate_api_key(
            api_key=x_api_key,
            db=db,
        )

    # --------------------------------------
    # VALIDACIONES FINALES
    # --------------------------------------
    if not user:
        raise credentials_exception

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    request.state.user_id = user.id

    return user


# ==========================================================
# PERMISSIONS
# ==========================================================


class PermissionChecker:
    def __init__(
        self,
        required_permission: str,
    ):
        self.required_permission = required_permission

    def __call__(
        self,
        current_user=Depends(get_current_user),
    ):
        user_roles = [
            link.role.name for link in current_user.user_roles_links if link.active
        ]

        # Admin bypass
        if "Admin" in user_roles:
            return current_user

        user_permissions = [permission.code for permission in current_user.permissions]

        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"No tienes el permiso necesario: " f"{self.required_permission}"
                ),
            )

        return current_user
