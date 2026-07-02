from uuid import UUID

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    file_name: str
    file_extension: str
    mime_type: str
    storage_type: str | None = None
    file_size: int | None = None
    file_path: str | None = None

    model_config = {"from_attributes": True}


class AttachmentContentResponse(AttachmentResponse):
    file_base64: str | None = None


class AttachmentCreateRequest(BaseModel):
    entity_type: str
    entity_id: UUID
    file_name: str
    file_extension: str
    mime_type: str
    storage_type: str | None = None
    file_size: int | None = None
    file_path: str | None = None
    file_base64: str | None = None


class AttachmentUpdateRequest(BaseModel):
    file_name: str | None = None
    file_extension: str | None = None
    mime_type: str | None = None
    storage_type: str | None = None
    file_size: int | None = None
    file_path: str | None = None
    file_base64: str | None = None
