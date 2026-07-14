
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Company Schemas
class CompanyCreateRequest(BaseModel):
    code: str
    name: str
    rut: str | None = None
    active: Optional[bool] = True
class CompanyResponse(CompanyCreateRequest):
    id: int
class CompanyUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    rut: Optional[str] = None
    active: Optional[bool] = None
# Area Schemas
class AreaCreateRequest(BaseModel):
    code: str
    name: str
    description: str
    active: Optional[bool] = True
class AreaUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
class AreaResponse(AreaCreateRequest):
    id: int
# Currency Schemas
class CurrencyCreateRequest(BaseModel):
    code: str=Field(..., max_length=3) 
    name: str=Field(..., max_length=50)
    symbol: str=Field(..., max_length=10)
    exchange_rate_to_base: Decimal = Decimal("1")
    is_base_currency: bool = False
    active: Optional[bool] = True

class CurrencyUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    exchange_rate_to_base: Optional[Decimal] = None
    is_base_currency: Optional[bool] = None
    active: Optional[bool] = None

class CurrencyResponse(CurrencyCreateRequest):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MailingParameterCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    template: str | None = None
    template_html: str | None = None
    template_text: str | None = None
    mp_from: str | None = Field(default=None, max_length=255)
    to: str | None = None
    subject: str | None = Field(default=None, max_length=255)
    cc: str | None = None
    bcc: str | None = None
    active: bool = True


class MailingParameterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    template: str | None = None
    template_html: str | None = None
    template_text: str | None = None
    mp_from: str | None = Field(default=None, max_length=255)
    to: str | None = None
    subject: str | None = Field(default=None, max_length=255)
    cc: str | None = None
    bcc: str | None = None
    active: bool | None = None


class MailingParameterResponse(MailingParameterCreateRequest):
    id: int
    model_config = ConfigDict(from_attributes=True)
