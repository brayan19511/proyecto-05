from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from app.core.db_postgres import get_db
from app.api.verify.seed_service import SeedService


router = APIRouter(prefix="/verify", tags=["Verify"])


@router.get("/seed")
async def seed(db:Session=Depends(get_db)):
    try:
        seed_service=SeedService(db)
        result=seed_service.run_seed()
        return result

    except Exception as e:
        return HTTPException(status_code=500, detail={"message": "Verification failed", "error": str(e)})   