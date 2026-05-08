# app/api/security/role/role_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.security.role.role_schemas import AssingnRoleToUserRequest, RoleRequest
from app.api.security.role.role_service import RoleService
from app.core.db_postgres import get_db


router = APIRouter(    prefix="/roles",    tags=["roles"],)

@router.get("/")
async def get_roles(db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.get_all_roles()
@router.post("/register")
async def create_role(data: RoleRequest, db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.create_role(data)
@router.get("/{role_id}")
async def get_role(role_id: str, db:Session=Depends(get_db)):
    router_service = RoleService(db)  # Replace with actual DB session
    return router_service.get_role(role_id)
@router.put("/{role_id}")
async def update_role(role_id: str, data: RoleRequest, db:Session=Depends(get_db)):
    service = RoleService(db)
    try:
        return service.update_role(role_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
@router.delete("/{role_id}")
async def delete_role(role_id: str, db:Session=Depends(get_db)):
    service = RoleService(db)
    try:
        service.delete_role(role_id)
        return {"message": "Role deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
@router.post("/assign-role")
def assign_role_to_user(role_request: AssingnRoleToUserRequest, db: Session = Depends(get_db)):
    """
    Assign a role to a user.

    - **user_id**: The ID of the user to whom the role will be assigned.
    - **role_id**: The ID of the role to be assigned.
    """
    role_service = RoleService(db)
    role_service.assign_role_to_user(role_request.user_id, role_request.role_id)
    return {"message": f"Role with ID {role_request.role_id} assigned to user with ID {role_request.user_id}."}