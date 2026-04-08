
# app/api/user/user_router.py

from uuid import UUID
from fastapi import APIRouter, Depends

from app.api.user.user_repository import UserRepository
from app.api.user.user_schemas import UserProfileResponse, UserProfileUpdate
from app.api.user.user_service import UserService
from app.core.db_postgres import get_db


router = APIRouter(   prefix="/users",tags=["users"],)

@router.get("/{user_id}",response_model=UserProfileResponse)
async def get_user(user_id: UUID,db=Depends(get_db)):
    user_servive=UserService(db)
    return user_servive.get_user_profile(user_id)
@router.patch("/{user_id}",response_model=UserProfileResponse)
async def update_user(user_id: UUID, user_update: UserProfileUpdate, db=Depends(get_db)):
    user_servive=UserService(db)
    return user_servive.update_profile(user_id, user_update)