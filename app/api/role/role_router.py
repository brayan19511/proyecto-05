

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.role.role_schemas import RoleRequest
from app.api.role.role_service import RoleService
from app.core.db_postgres import get_db


router = APIRouter(    prefix="/roles",    tags=["roles"],)

@router.get("/")
async def get_roles(db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.get_all_roles()
@router.post("/")
async def create_role(data: RoleRequest, db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.create_role(data)
@router.get("/{role_id}")
async def get_role(role_id: str, db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.get_role(role_id)
@router.put("/{role_id}")
async def update_role(role_id: str, data: RoleRequest, db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.update_role(role_id, data)
@router.delete("/{role_id}")
async def delete_role(role_id: str, db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.delete_role(role_id)