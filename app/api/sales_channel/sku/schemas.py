from datetime import datetime

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class SkuCreateRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=255)
    external_id: str | None = Field(default=None, max_length=255)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip()

    @field_validator("external_id")
    @classmethod
    def normalize_external_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SkuUpdateRequest(BaseModel):
    external_id: str | None = Field(default=None, max_length=255)

    @field_validator("external_id")
    @classmethod
    def normalize_external_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar")
        return self


class SkuResponse(BaseModel):
    sku: str
    external_id: str | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BulkSkuItem(BaseModel):
    sku: str = Field(min_length=1, max_length=255)
    active: bool = Field(
        validation_alias=AliasChoices(
            "active",
            "is_active",
            "on",
            "on_off",
            "on/off",
        )
    )

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip()


class BulkSkuSyncRequest(BaseModel):
    items: list[BulkSkuItem] = Field(min_length=1, max_length=20_000)
    deactivate_missing: bool = False
    create_missing: bool = True

    @model_validator(mode="after")
    def reject_duplicate_skus(self):
        normalized = [item.sku.casefold() for item in self.items]
        if len(normalized) != len(set(normalized)):
            raise ValueError("La lista contiene SKU duplicados")
        return self


class BulkSkuSyncResponse(BaseModel):
    received: int
    created: int
    activated: int
    deactivated: int
    unchanged: int
    missing: list[str]


class ActiveSkuSnapshotRequest(BaseModel):
    skus: list[str] = Field(min_length=1, max_length=20_000)
    create_missing: bool = True

    @field_validator("skus")
    @classmethod
    def normalize_and_validate_skus(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 255 for value in normalized):
            raise ValueError(
                "Cada SKU debe contener entre 1 y 255 caracteres"
            )

        comparable = [value.casefold() for value in normalized]
        if len(comparable) != len(set(comparable)):
            raise ValueError("La lista contiene SKU duplicados")
        return normalized
