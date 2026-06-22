from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.storage.attachments_repository import AttachmentRepository
from app.api.storage.attachments_schema import AttachmentUpdateRequest


class AttachmentService:
    def __init__(self, db: Session):
        self.repository = AttachmentRepository(db)

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ):
        return self.repository.get_by_entity(entity_type, entity_id)

    def get_by_id(
        self,
        attachment_id: UUID,
    ):
        return self._get_or_404(attachment_id)

    def update(
        self,
        attachment_id: UUID,
        request: AttachmentUpdateRequest,
    ):
        attachment = self._get_or_404(attachment_id)
        data = request.model_dump(exclude_unset=True)

        return self.repository.update(attachment, data)

    def delete(
        self,
        attachment_id: UUID,
    ):
        attachment = self._get_or_404(attachment_id)
        self.repository.delete(attachment)

        return True

    def _get_or_404(
        self,
        attachment_id: UUID,
    ):
        attachment = self.repository.get_by_id(attachment_id)

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado",
            )

        return attachment
