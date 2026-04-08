from fastapi import FastAPI

from app.api.auth import auth_router
from app.api.role import role_router
from app.api.user import user_router

app = FastAPI(title="Proyecto 05", description="A simple FastAPI application", version="1.0.0")
    
app.include_router(prefix="/api",router=role_router.router)
app.include_router(prefix="/api",router=auth_router.router)
app.include_router(prefix="/api",router=user_router.router)