from fastapi import APIRouter

from app.api.coolbox.analytics import analytics_router
from app.api.coolbox.ETL import etl_router

router = APIRouter()


router.include_router(prefix="/etl", router=etl_router.router)
router.include_router(prefix="/analytics", router=analytics_router.router)
