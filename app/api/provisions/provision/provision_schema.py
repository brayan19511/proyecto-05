# app/api/provisions/provision/provision_schema.py
from datetime import date
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID


# Status Provision
class ProvisionStatusReq(BaseModel):
    code: str
    name: str | None = None
    active: bool | None = None

class ProvisionStatusResponse(ProvisionStatusReq):
    id: int
# Attachment
class AttachmentRequest(BaseModel):
    entity_type: str
    file_name: str
    file_extension: str
    mime_type: str

    storage_type: str | None = None
    file_size: int | None = None

    file_path: str | None = None
    file_base64: str | None = None

# Provision Document

class ProvisionDocumentRequest(BaseModel):
    provision_id: UUID
    document_type: str | None = None
    document_number: str | None = None

    supplier_tax_id: str | None = None
    supplier_name: str | None = None

    amount: Decimal
    currency_id: int
    attachments: list[AttachmentRequest] = []
    
class ProvisionDocumentResponse(ProvisionDocumentRequest):
    id: int


# Provision
class ProvisionCreateRequest(BaseModel):
    ticket_code: str
    description: str | None = None

    concept_id: int
    status_id: int
    area_id: int
    currency_id: int
    company_id: int

    amount: Decimal
    provision_date: date

    observations: str | None = None
    
    documents: list[ProvisionDocumentRequest] = []

class ProvisionResponse(ProvisionCreateRequest):
    id: UUID

