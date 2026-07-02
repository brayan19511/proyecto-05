from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.provisions.provision.provision_service import ProvisionService
from app.api.storage.attachments_repository import AttachmentRepository
from app.api.storage.attachments_schema import (
    AttachmentCreateRequest,
    AttachmentUpdateRequest,
)
from app.api.storage.constants import ALLOWED_ATTACHMENT_ENTITY_TYPES
from app.models.storage import Attachment


class AttachmentService:
    def __init__(self, db: Session):
        self.repository = AttachmentRepository(db)
        self.provision_service = ProvisionService(db)

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID,
        can_view_all: bool = False,
    ):
        self.provision_service.ensure_entity_access(
            entity_type,
            entity_id,
            user_id,
            can_view_all=can_view_all,
        )
        return self.repository.get_by_entity(entity_type, entity_id)

    def get_by_id(
        self,
        attachment_id: UUID,
        user_id: UUID,
        can_view_all: bool = False,
    ):
        attachment = self._get_or_404(attachment_id)
        self.provision_service.ensure_entity_access(
            attachment.entity_type,
            attachment.entity_id,
            user_id,
            can_view_all=can_view_all,
        )
        return attachment

    def create(
        self,
        request: AttachmentCreateRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        if request.entity_type not in ALLOWED_ATTACHMENT_ENTITY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de entidad no soportado para archivos",
            )

        self.provision_service.ensure_entity_access(
            request.entity_type,
            request.entity_id,
            user_id,
            write=True,
            can_edit_all=can_edit_all,
        )

        attachment = Attachment(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            file_name=request.file_name,
            file_extension=request.file_extension,
            mime_type=request.mime_type,
            storage_type=request.storage_type,
            file_size=request.file_size,
            file_path=request.file_path,
            file_base64=request.file_base64,
            created_by=user_id,
        )

        return self.repository.create(attachment)

    def update(
        self,
        attachment_id: UUID,
        request: AttachmentUpdateRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        attachment = self._get_or_404(attachment_id)
        self.provision_service.ensure_entity_access(
            attachment.entity_type,
            attachment.entity_id,
            user_id,
            write=True,
            can_edit_all=can_edit_all,
        )
        data = request.model_dump(exclude_unset=True)
        attachment.updated_by = user_id

        return self.repository.update(attachment, data)

    def delete(
        self,
        attachment_id: UUID,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        attachment = self._get_or_404(attachment_id)
        self.provision_service.ensure_entity_access(
            attachment.entity_type,
            attachment.entity_id,
            user_id,
            write=True,
            can_edit_all=can_edit_all,
        )
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
