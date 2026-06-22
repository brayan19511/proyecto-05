# app/api/provisions/provision/provision_schema.py
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ProvisionStatusReq(BaseModel):
    code: str
    name: str | None = None
    active: bool | None = None


class ProvisionStatusResponse(ProvisionStatusReq):
    id: int


class AttachmentRequest(BaseModel):
    entity_type: str | None = None
    file_name: str
    file_extension: str
    mime_type: str
    storage_type: str | None = None
    file_size: int | None = None
    file_path: str | None = None
    file_base64: str | None = None


class ProvisionDocumentRequest(BaseModel):
    document_type: str | None = None
    document_number: str | None = None
    document_date: date | None = None
    description: str | None = None
    supplier_tax_id: str | None = None
    supplier_name: str | None = None
    amount: Decimal
    currency_id: int
    attachments: list[AttachmentRequest] = Field(default_factory=list)


class ProvisionDocumentUpdateRequest(BaseModel):
    document_type: str | None = None
    document_number: str | None = None
    document_date: date | None = None
    description: str | None = None
    supplier_tax_id: str | None = None
    supplier_name: str | None = None
    amount: Decimal | None = None
    currency_id: int | None = None


class ProvisionDocumentResponse(BaseModel):
    id: UUID
    document_type: str | None = None
    document_number: str | None = None
    document_date: date | None = None
    description: str | None = None
    supplier_tax_id: str | None = None
    supplier_name: str | None = None
    amount: Decimal
    currency_id: int
    exchange_rate_to_base: Decimal | None = None
    amount_base: Decimal | None = None

    model_config = {"from_attributes": True}


class ProvisionAccessRequest(BaseModel):
    user_id: UUID
    access_type: str = "viewer"


class ProvisionAccessResponse(BaseModel):
    id: int
    user_id: UUID
    access_type: str
    active: bool

    model_config = {"from_attributes": True}


class ProvisionCreateRequest(BaseModel):
    ticket_code: str
    description: str | None = None
    supplier_tax_id: str | None = None
    supplier_name: str | None = None
    concept_id: int
    area_id: int
    currency_id: int
    company_id: int
    amount: Decimal
    provision_date: date
    observations: str | None = None
    access: list[ProvisionAccessRequest] = Field(default_factory=list)
    documents: list[ProvisionDocumentRequest] = Field(default_factory=list)


class ProvisionUpdateRequest(BaseModel):
    description: str | None = None
    supplier_tax_id: str | None = None
    supplier_name: str | None = None
    concept_id: int | None = None
    area_id: int | None = None
    currency_id: int | None = None
    amount: Decimal | None = None
    provision_date: date | None = None
    observations: str | None = None


class ProvisionActionRequest(BaseModel):
    comments: str | None = None


class ProvisionSummaryResponse(BaseModel):
    id: UUID
    ticket_code: str
    description: str | None = None
    supplier_tax_id: str | None = None
    supplier_name: str | None = None
    status_id: int
    concept_id: int
    area_id: int
    currency_id: int
    currency_code: str | None = None
    base_currency_code: str = "PEN"
    company_id: int
    expected_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    expected_amount_base: Decimal
    actual_amount_base: Decimal
    variance_amount_base: Decimal
    variance_status: str
    provision_date: date
    observations: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    closed_at: datetime | None = None


class ProvisionDetailResponse(ProvisionSummaryResponse):
    documents: list[ProvisionDocumentResponse] = Field(default_factory=list)
    access: list[ProvisionAccessResponse] = Field(default_factory=list)
