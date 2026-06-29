from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


DEFAULT_SCOPES = ["analytics.read"]


class ApiClientCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    user_id: UUID | None = None
    scopes: list[str] = Field(default_factory=lambda: DEFAULT_SCOPES.copy())
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def normalize_expiration(cls, value: datetime | None):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ApiClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=100)
    scopes: list[str] | None = None
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def normalize_expiration(cls, value: datetime | None):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ApiClientStatusUpdate(BaseModel):
    active: bool


class ApiClientAssign(BaseModel):
    user_id: UUID


class ApiClientResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ApiClientSecretResponse(ApiClientResponse):
    api_key: str
    warning: str = "Guarde esta clave ahora; no volvera a mostrarse."
