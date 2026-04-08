



from typing import Optional

from pydantic import BaseModel, ConfigDict


class RoleRequest(BaseModel):
    name: str
    system_name: Optional[str] = None
    active: bool = True
    
class RoleResponse(BaseModel):
    id: int
    name: str
    system_name: Optional[str] = None
    active: bool
    
    model_config = ConfigDict(from_attributes=True)


