from pydantic import BaseModel, ConfigDict


class PermisionCreateRequest(BaseModel):
    code: str
    description: str


class PermissionUpdateRequest(BaseModel):
    code: str | None = None
    description: str | None = None
    active: bool | None = None


class PermisionResponse(BaseModel):
    id: int
    code: str
    description: str
    active: bool
    model_config = ConfigDict(from_attributes=True)


class AssignRoleToPermissionRequest(BaseModel):
    permission_id: int
    role_id: int
