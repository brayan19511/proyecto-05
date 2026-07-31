from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.schemas import ORMModel


class ApiKeyCreateRequest(BaseModel):
    name: str
    expires_at: datetime | None = None


class ApiKeyUpdateRequest(BaseModel):
    name: str | None = None
    expires_at: datetime | None = None
    active: bool | None = None


class ApiKeyResponse(ORMModel):
    id: UUID
    name: str
    active: bool
    expires_at: datetime | None


class ApiKeyCreatedResponse(BaseModel):
    api_key: str
    key_info: ApiKeyResponse
