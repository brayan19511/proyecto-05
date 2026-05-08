
# app/api/user/user_router.py

from uuid import UUID
from fastapi import APIRouter, Depends

from app.api.user import  UserService, UserProfileCreate, UserProfileResponse,UserProfileUpdate
from app.core.db_postgres import get_db
from app.core.security import PermissionChecker

router = APIRouter(   prefix="/users",tags=["users"],)
@router.get("/getall",response_model=list[UserProfileResponse])
async def get_users(db=Depends(get_db),current_user = Depends(PermissionChecker("sap.read"))):
    user_servive=UserService(db)
    return user_servive.get_users()

@router.get("/{user_id}",response_model=UserProfileResponse)
async def get_user(user_id: UUID,db=Depends(get_db)):
    user_servive=UserService(db)
    return user_servive.get_user_profile(user_id)
@router.post("/{user_id}",response_model=UserProfileResponse)
async def create_user(user_id: UUID, user_create: UserProfileCreate, db=Depends(get_db)):
    user_servive=UserService(db)
    return user_servive.create_user_profile(user_id,user_create)
@router.patch("/{user_id}",response_model=UserProfileResponse)
async def update_user(user_id: UUID, user_update: UserProfileUpdate, db=Depends(get_db)):
    user_servive=UserService(db)
    return user_servive.update_profile(user_id, user_update)