from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.schemas import PageResponse


class MarkType(StrEnum):
    ENTRY = "INGRESO"
    EXIT = "SALIDA"


class AttendanceMarkResponse(BaseModel):
    sequence_id: int
    document_number: int
    marked_at: datetime
    mark_date: date
    row_number: int
    mark_type: MarkType


class AttendanceMarkSearch(BaseModel):
    """Filters accepted by the bulk attendance search endpoint."""

    document_numbers: list[int] = Field(min_length=1, max_length=100)
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=1000, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)


AttendanceMarkPage = PageResponse[AttendanceMarkResponse]
