from enum import StrEnum

from pydantic import BaseModel, Field


class SkuImportMode(StrEnum):
    ACTIVE_SNAPSHOT = "active_snapshot"
    STATUS_UPDATE = "status_update"
    PROMOTION_SNAPSHOT = "promotion_snapshot"


class SkuImportIssue(BaseModel):
    row: int | None = None
    field: str | None = None
    message: str


class SkuImportResponse(BaseModel):
    filename: str
    sha256: str
    mode: SkuImportMode
    preview: bool
    can_apply: bool
    applied: bool
    received: int
    valid: int
    created: int = 0
    activated: int = 0
    deactivated: int = 0
    unchanged: int = 0
    promotions_added: int = 0
    promotions_removed: int = 0
    missing: list[str] = Field(default_factory=list)
    # Detalle de que SKUs se estan creando / activando / desactivando.
    created_skus: list[str] = Field(default_factory=list)
    activated_skus: list[str] = Field(default_factory=list)
    deactivated_skus: list[str] = Field(default_factory=list)
    # Nombre del articulo por SKU (desde la ICG del pais del canal). El front lo
    # muestra junto al SKU. Puede venir vacio para SKUs sin match o si ICG no
    # respondio. `descriptions_truncated` avisa si se omitieron por tope.
    descriptions: dict[str, str] = Field(default_factory=dict)
    descriptions_truncated: bool = False
    errors: list[SkuImportIssue] = Field(default_factory=list)
