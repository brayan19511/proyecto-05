# app/api/provisions/provision_document/provision_document_router.py
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/provision",
    tags=["Provision"],
)
# creacion crud de la cavecera de provision document
@router.get("/document")
async def get_provision_document():
    return {"message": "Get provision document"}
# creacion crud de los docuementos asociados a la provision document
@router.post("/document")
async def create_provision_document():
    return {"message": "Create provision document"}
