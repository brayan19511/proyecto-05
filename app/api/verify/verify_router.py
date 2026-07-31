import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.verify.seed_service import SeedService
from app.core.db.db_postgres import get_db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/verify", tags=["VERIFICACION"])


@router.get("/seed")
async def seed(db: Session = Depends(get_db)):
    try:
        return SeedService(db).run_seed()
    except Exception as exc:
        logger.exception("Error ejecutando verificacion y seed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo completar la verificacion inicial",
        ) from exc


@router.get("/debug-ip")
def debug_ip(request: Request):
    return {
        "client": request.client.host if request.client else None,
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_real_ip": request.headers.get("x-real-ip"),
    }
