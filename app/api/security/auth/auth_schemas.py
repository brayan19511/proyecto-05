# app/api/security/auth/auth_schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from uuid import UUID
from typing import  Literal, Optional

from app.api.security.user_scope.user_scope_schema import CompanyScopeResponse

# Lo que el usuario envía para loguearse
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserTokenResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    roles: Optional[list[str]] = []

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # user: UserTokenResponse

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


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=4)
    
class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    active: bool
    roles: list[str]
    permissions: list[str]
    # Alcance operativo del usuario, agrupado como empresa > areas.
    companies: list[CompanyScopeResponse] = []
    # True para admin: ve todas las empresas y areas.
    unrestricted_scope: bool = False
