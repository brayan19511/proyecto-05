
from typing import Optional
from pydantic import BaseModel, ConfigDict

class RoleRequest(BaseModel):
    name: str
    active: bool = True
class RoleResponse(BaseModel):
    id: int
    name: str
    active: bool
    model_config = ConfigDict(from_attributes=True)


