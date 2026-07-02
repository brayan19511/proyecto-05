from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.sales_channel.sku.schemas import SkuResponse


class PeyaSkuResponse(SkuResponse):
    has_promotion: bool


class PromoSkuCreateRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=255)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip()


class PromoSkuResponse(BaseModel):
    sku: str

    model_config = ConfigDict(from_attributes=True)
