from fastapi import APIRouter

from app.api.finance.libro_mayor import libro_mayor_router
from app.api.finance.payment_provider import payment_provider_router
from app.api.finance.provisions import provisions_router

router = APIRouter()
router.include_router(libro_mayor_router.router)
router.include_router(provisions_router.router)
router.include_router(payment_provider_router.router)
