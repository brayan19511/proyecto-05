
from fastapi import APIRouter

from app.api.provisions.concepts import concepts_router


router = APIRouter()

router.include_router(concepts_router.router, prefix="/concepts", tags=["Provisions"])