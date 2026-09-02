from fastapi import APIRouter, Depends

from app.api.finance.libro_mayor import libro_mayor_router
from app.api.finance.payment_provider import payment_provider_router
from app.api.finance.provisions import provisions_router
from app.core.modules import (
    MODULE_LEDGER,
    MODULE_PAYMENT_PROVIDER,
    MODULE_PROVISIONS,
    ModuleEnabled,
)

# El interruptor se declara en el include y no dentro de cada sub-router: asi
# cubre tambien los routers anidados (provisiones incluye conceptos).
router = APIRouter()
router.include_router(
    libro_mayor_router.router,
    dependencies=[Depends(ModuleEnabled(MODULE_LEDGER))],
)
router.include_router(
    provisions_router.router,
    dependencies=[Depends(ModuleEnabled(MODULE_PROVISIONS))],
)
router.include_router(
    payment_provider_router.router,
    dependencies=[Depends(ModuleEnabled(MODULE_PAYMENT_PROVIDER))],
)
