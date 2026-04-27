# app/api/security/security_router.py
from fastapi import APIRouter
from app.api.security.auth import auth_router
from app.api.security.permission import permission_router
from app.api.security.role import role_router

router = APIRouter()
# Aquí incluyes los sub-routers de seguridad
router.include_router(auth_router.router, prefix="/security")
router.include_router(permission_router.router, prefix="/security")
router.include_router(role_router.router, prefix="/security")