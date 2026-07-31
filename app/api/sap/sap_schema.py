from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
)

from app.api.sap.constants import SAP_RESOURCE_PATTERN
from app.core.config import settings



PositiveDocumentNumber = Annotated[int, Field(gt=0)]


class SapServiceDocumentos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=1, max_length=200)
    database: str
    entidad: str
    action: str
    documentos: list[PositiveDocumentNumber] = Field(
        min_length=1,
        max_length=settings.SAP_JOB_MAX_DOCUMENTS,
    )

    @field_validator("database", "entidad", "action")
    @classmethod
    def validate_resource_name(cls, value: str) -> str:
        normalized = value.strip()
        if not SAP_RESOURCE_PATTERN.fullmatch(normalized):
            raise ValueError("Contiene caracteres no permitidos")
        return normalized
