# app/api/provisions/provision/provision_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db_postgres import get_db
from app.api.provisions.provision.provision_schema import ProvisionCreateRequest
from app.api.provisions.provision.provision_service import ProvisionService
router = APIRouter(
    tags=["Provision"],
)

@router.post("")
def create_provision(
    request: ProvisionCreateRequest,
    db: Session = Depends(get_db),
):

    service = ProvisionService(db)

    provision = service.create_provision(
        request=request,
        user_id=1,
    )

    return {
        "message": "Provision creada correctamente",
        "id": provision.id
    }