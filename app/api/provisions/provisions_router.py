
from fastapi import APIRouter

from app.api.provisions.concepts import concepts_router
from app.api.provisions.provision import provision_router


router = APIRouter()

router.include_router(concepts_router.router, prefix="/provisions/concepts", tags=["PROVISIONES CONCEPTOS"])
router.include_router(provision_router.router, prefix="/provisions", tags=["PROVISIONES"])