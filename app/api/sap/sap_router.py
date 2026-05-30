
from fastapi import APIRouter

from app.api.sap.finance import sap_finance_router



router = APIRouter()

router.include_router(sap_finance_router.router, prefix="/sap", tags=["SAP"])