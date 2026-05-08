# app/core/security.py
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request,status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
import jwt
from sqlalchemy.orm import Session
from app.api.security.auth.auth_repository import AuthRepository
from app.core.config import settings
from app.core.db_postgres import get_db


pwd_context = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=minutes or settings.JWT_EXPIRES_MIN)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(request: Request,
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. Decodificar el token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # 2. BUSCAR AL USUARIO (Aquí usamos el Repositorio)
    repository = AuthRepository(db)
    user = repository.get_by_id(user_id)
    
    if user is None:
        raise credentials_exception
    
    if not user.active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    request.state.user_id = user.id
    return user # Retorna el objeto Auth completo

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user = Depends(get_current_user)):
        # 1. El superusuario o Admin total siempre pasa
        # Asumiendo que tus roles tienen nombres fijos para el "admin" del sistema
        user_roles = [link.role.name for link in current_user.user_roles_links if link.active]
        if "Admin" in user_roles:
            return current_user

        # 2. Verificamos los permisos individuales
        # Gracias a la @property 'permissions' que creamos en tu modelo Auth
        user_permissions = [p.code for p in current_user.permissions]
        
        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes el permiso necesario: {self.required_permission}"
            )
        
        return current_user