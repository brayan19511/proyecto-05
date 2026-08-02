from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class AnalyticsIngestionMode(StrEnum):
    INCREMENTAL = "incremental"
    REPROCESS = "reprocess"
    SNAPSHOT = "snapshot"


class IcgIngestionRequest(BaseModel):
    table_name: str | None = Field(default=None, min_length=1, max_length=120)
    table_names: list[str] | None = None
    table_group: str | None = Field(default=None, pattern="^(transactional|master|all)$")
    mode: AnalyticsIngestionMode = AnalyticsIngestionMode.INCREMENTAL
    start_date: date | None = None
    end_date: date | None = None
    lookback_days: int | None = Field(default=None, ge=0, le=31)
    batch_size: int = Field(default=1, ge=1, le=31)
    idempotency_key: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_dates(self):
        selectors = [
            self.table_name is not None,
            bool(self.table_names),
            self.table_group is not None,
        ]
        if sum(selectors) != 1:
            raise ValueError("Indica solo uno: table_name, table_names o table_group")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date no puede ser menor que start_date")
        if self.mode == AnalyticsIngestionMode.REPROCESS:
            if not self.start_date or not self.end_date:
                raise ValueError("start_date y end_date son obligatorios para reproceso")
        return self


class IcgTableResponse(BaseModel):
    name: str
    kind: str
    master_storage_mode: str | None = None


class IcgCatalogResponse(BaseModel):
    items: list[IcgTableResponse]


class IcgSilverBuildRequest(BaseModel):
    start_date: date
    end_date: date | None = None
    batch_size: int = Field(default=1, ge=1, le=31)
    idempotency_key: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_range(self):
        resolved_end = self.end_date or self.start_date
        if resolved_end < self.start_date:
            raise ValueError("end_date no puede ser menor que start_date")
        self.end_date = resolved_end
        return self


class IcgSilverBuildItemResponse(BaseModel):
    dataset_name: str
    business_date: date
    output_path: str
    rows_count: int


class IcgSilverBuildResponse(BaseModel):
    items: list[IcgSilverBuildItemResponse]
