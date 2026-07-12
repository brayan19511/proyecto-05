from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.core.db.db_postgres import get_db
from app.api.verify.seed_service import SeedService
from app.core.security import PermissionChecker


router = APIRouter(prefix="/verify", tags=["Verify"])


@router.post("/seed")
def seed(
    db: Session = Depends(get_db),
    # _current_user=Depends(PermissionChecker("security.roles.edit")),
):
    """Reconcile base security data. Initial bootstrap is done through the CLI."""
    return SeedService(db).run_seed()
