
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
    
class AssingnRoleToUserRequest(BaseModel):
    user_id: UUID
    role_id: int
    
    