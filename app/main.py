# app/main.py
from fastapi import FastAPI

from app.api.security import security_router
from app.api.user import user_router
from app.api.verify import verify_router
from app.core.handlers import register_exception_handlers
from app.core.middleware import AuditMiddleware

app = FastAPI(title="Proyecto 05", description="Proyecto 05", version="1.0.0")

# =========================================================
# 1. REGISTRO DE MIDDLEWARES
# =========================================================
# Se añade antes de los routers para que capture todo el flujo
app.add_middleware(AuditMiddleware)

# =========================================================
# 2. MANEJO DE EXCEPCIONES
# =========================================================
register_exception_handlers(app)

# =========================================================
# 3. RUTAS (ROUTERS)
# =========================================================
app.include_router(prefix="/api", router=verify_router.router)
app.include_router(prefix="/api", router=security_router.router)
app.include_router(prefix="/api", router=user_router.router)