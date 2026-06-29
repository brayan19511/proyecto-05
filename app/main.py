# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import health_router
from app.api.libro_mayor import libro_mayor_router
from app.api.master import master_router
from app.api.provisions import provisions_router
from app.api.sales_channel import sales_channel_router
from app.api.sap import sap_router
from app.api.security import security_router
from app.api.storage import attachments_router
from app.api.user import user_router
from app.api.verify import verify_router
from app.api.web import web_router
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.middleware import AuditMiddleware

app = FastAPI(title=settings.PROJECT_NAME)

# =========================================================
# 1. CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =========================================================
# 2. REGISTRO DE MIDDLEWARES
# =========================================================
# Se añade antes de los routers para que capture todo el flujo
app.add_middleware(AuditMiddleware)

# =========================================================
# 3. MANEJO DE EXCEPCIONES
# =========================================================
register_exception_handlers(app)

# =========================================================
# 4. RUTAS (ROUTERS)
# =========================================================
app.include_router(prefix="/api", router=sap_router.router)
app.include_router(prefix="/api", router=web_router.router)
app.include_router(prefix="/api", router=libro_mayor_router.router)
app.include_router(prefix="/api", router=provisions_router.router)
app.include_router(prefix="/api", router=master_router.router)
app.include_router(prefix="/api", router=verify_router.router)
app.include_router(prefix="/api", router=security_router.router)
app.include_router(prefix="/api", router=attachments_router.router)
app.include_router(prefix="/api", router=user_router.router)
app.include_router(prefix="/api", router=sales_channel_router.router)
app.include_router(router=health_router.router)
