# app/core/security.py
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException,status
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

def get_current_user(
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
        
    return user # Retorna el objeto Auth completo