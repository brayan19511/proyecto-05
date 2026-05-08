# app/api/security/permission/permission_schemas.py
from uuid import UUID

from pydantic import BaseModel

class PermisionCreateRequest(BaseModel):
    code: str
    description: str
class PermisionResponse(BaseModel):
    id: int
    code: str
    description: str
    active: bool
    
class AssignRoleToPermissionRequest(BaseModel):
    permission_id: int
    role_id: int
    
    