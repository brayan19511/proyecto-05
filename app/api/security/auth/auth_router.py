# app/api/security/auth/auth_router.py
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session
from app.api.security.auth.auth_schemas import *
from app.api.security.auth.auth_service import AuthService
from app.core.db_postgres import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.authenticate_user(login_data)
@router.post("/register")
def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register_user(user_data)
