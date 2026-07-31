from datetime import date

from sqlalchemy.orm import Session

from app.api.attendance.repository import AttendanceRepository
from app.api.attendance.schemas import AttendanceMarkPage
from app.core.exceptions import ValidationError


MAX_DOCUMENTS_PER_QUERY = 100
MAX_DATE_RANGE_DAYS = 366


class AttendanceService:
    def __init__(self, db: Session):
        self.repository = AttendanceRepository(db)

    def get_marks(
        self,
        document_numbers: list[int],
        date_from: date | None,
        date_to: date | None,
        limit: int,
        offset: int,
    ) -> AttendanceMarkPage:
        normalized_documents = list(dict.fromkeys(document_numbers))
        if not normalized_documents:
            raise ValidationError("Debe indicar al menos un documento")
        if len(normalized_documents) > MAX_DOCUMENTS_PER_QUERY:
            raise ValidationError(
                f"Solo se permiten {MAX_DOCUMENTS_PER_QUERY} documentos"
            )
        if any(document <= 0 for document in normalized_documents):
            raise ValidationError("Los documentos deben ser numeros positivos")
        if date_from and date_to:
            if date_from > date_to:
                raise ValidationError(
                    "date_from no puede ser posterior a date_to"
                )
            if (date_to - date_from).days > MAX_DATE_RANGE_DAYS:
                raise ValidationError(
                    f"El rango maximo es de {MAX_DATE_RANGE_DAYS} dias"
                )

        items, total = self.repository.get_marks(
            normalized_documents,
            date_from,
            date_to,
            limit,
            offset,
        )
        return AttendanceMarkPage.build(items, total, limit, offset)
