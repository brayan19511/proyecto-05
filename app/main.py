# app/main.py
from fastapi import FastAPI

from app.api.security import security_router
from app.api.user import user_router
from app.api.verify import verify_router
from app.core.handlers import register_exception_handlers

app = FastAPI(title="Proyecto 05", description="Proyecto 05", version="1.0.0")

register_exception_handlers(app)
    
app.include_router(prefix="/api",router=verify_router.router)
app.include_router(prefix="/api",router=security_router.router)
app.include_router(prefix="/api",router=user_router.router)
