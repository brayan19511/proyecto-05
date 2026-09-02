
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Company Schemas
class CompanyCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    rut: str | None = Field(default=None, max_length=20)
    active: Optional[bool] = True


class CompanyResponse(BaseModel):
    id: int
    code: str
    name: str
    rut: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdateRequest(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rut: Optional[str] = Field(default=None, max_length=20)
    active: Optional[bool] = None


# Area Schemas
class AreaCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    active: Optional[bool] = True


class AreaUpdateRequest(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    active: Optional[bool] = None


class AreaResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)
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

class CurrencyResponse(BaseModel):
    id: int
    code: str
    name: str
    symbol: str
    exchange_rate_to_base: Decimal
    is_base_currency: bool
    active: bool

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


# =====================================================
# MODULOS (interruptor de encendido/apagado)
# =====================================================
class ModuleResponse(BaseModel):
    code: str
    name: str
    description: str | None = None
    enabled: bool
    disabled_reason: str | None = None
    # True cuando el apagado viene del .env: el panel debe mostrarlo apagado
    # y sin poder prenderlo, porque la tabla no manda en ese caso.
    locked_by_environment: bool = False

    model_config = ConfigDict(from_attributes=True)


class ModuleUpdateRequest(BaseModel):
    enabled: bool
    # Motivo opcional que se muestra en el 503 y queda en la auditoria.
    disabled_reason: str | None = Field(default=None, max_length=255)
