# app/api/user/user_schemas.py
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional
from datetime import date, datetime

class UserProfileCreate(BaseModel):
    name: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    document_type: Optional[Literal["none", "DNI", "PASS", "CEX"]] = None
    document_number: Optional[str] = None
    @field_validator("birthday", mode="before")
    @classmethod
    def parse_birthday(cls, v):
        if isinstance(v, str) and v.strip():
            # Lista de formatos que quieres soportar
            formats = [
                "%d/%m/%Y",  # 16/01/2002
                "%Y-%m-%d",  # 2002-01-16
                "%Y/%m/%d",  # 2002/01/16 (El que quieres agregar)
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            
            # Si llega aquí es porque no coincidió con ninguno
            raise ValueError("Formato de fecha no reconocido. Use DD/MM/YYYY o YYYY-MM-DD")
        return v
class UserProfileUpdate(UserProfileCreate):
    pass

class UserProfileResponse(UserProfileUpdate):
    user_id: UUID
    email: str
    model_config = ConfigDict(from_attributes=True)