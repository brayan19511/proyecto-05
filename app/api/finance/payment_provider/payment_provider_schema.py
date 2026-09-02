from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


class PaymentProviderCreateRequest(BaseModel):
    tax_id: str = Field(min_length=1, max_length=20)
    legal_name: str = Field(min_length=1, max_length=255)
    commercial_names: list[str] = Field(default_factory=list)
    emails_payments: list[str] = Field(default_factory=list)
    active: bool = True

    @field_validator("tax_id", "legal_name", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("commercial_names", "emails_payments")
    @classmethod
    def strip_lists(cls, values):
        return _strip_list(values)


class PaymentProviderUpdateRequest(BaseModel):
    tax_id: str | None = Field(default=None, min_length=1, max_length=20)
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    commercial_names: list[str] | None = None
    emails_payments: list[str] | None = None
    active: bool | None = None

    @field_validator("tax_id", "legal_name", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("commercial_names", "emails_payments")
    @classmethod
    def strip_lists(cls, values):
        return _strip_list(values) if values is not None else values


class PaymentProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tax_id: str
    legal_name: str
    commercial_names: list[str]
    emails_payments: list[str]
    active: bool


class SentAttachmentResponse(BaseModel):
    """Constancia archivada tal como la ve el front.

    No expone file_path a proposito: es una ruta interna del servidor y el
    front no la necesita, descarga por /payments/attachments/{id}/content.
    """

    id: UUID
    file_name: str
    mime_type: str
    file_size: int | None = None

    model_config = ConfigDict(from_attributes=True)
