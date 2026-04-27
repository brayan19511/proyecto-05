# app/api/security/auth/auth_schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from uuid import UUID
from typing import  Literal, Optional

# Lo que el usuario envía para loguearse
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID

# Para mostrar información básica del usuario en el token o respuesta
class UserAuthSchema(BaseModel):
    id: UUID
    email: EmailStr
    active: bool
    
    model_config = ConfigDict(from_attributes=True)
    
class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=4)