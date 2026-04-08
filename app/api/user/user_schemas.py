# app/api/user/user_schemas.py
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional
from datetime import date

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    document_type: Optional[Literal["none", "DNI", "PASS", "CEX"]] = None
    document_number: Optional[str] = None

class UserProfileResponse(UserProfileUpdate):
    user_id: UUID
    email: str
    model_config = ConfigDict(from_attributes=True)