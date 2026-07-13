

from pydantic import BaseModel, Field


class AttachmentRequest(BaseModel):
    entity_type: str | None = None
    file_name: str
    file_extension: str
    mime_type: str
    storage_type: str | None = None
    file_size: int | None = None
    file_path: str | None = None
    file_base64: str | None = None
class PaymentProviderRequest(BaseModel):
    attachments: list[AttachmentRequest] = Field(default_factory=list)
    