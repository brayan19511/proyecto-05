from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApiKeyCreateRequest(BaseModel):
    name: str
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    active: bool
    expires_at: datetime | None

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(BaseModel):
    api_key: str
    key_info: ApiKeyResponse