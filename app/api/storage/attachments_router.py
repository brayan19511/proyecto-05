from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.storage.attachments_schema import (
    AttachmentContentResponse,
    AttachmentResponse,
    AttachmentUpdateRequest,
)
from app.api.storage.attachments_service import AttachmentService
from app.core.db.db_postgres import get_db
from app.core.security import PermissionChecker, get_current_user

router = APIRouter(prefix="/storage/attachments", tags=["Attachments"])


def get_service(db=Depends(get_db)):
    return AttachmentService(db)


@router.get("", response_model=list[AttachmentResponse])
def get_attachments_by_entity(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    service: AttachmentService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.get_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
    )


@router.get("/{attachment_id}", response_model=AttachmentResponse)
def get_attachment(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.get_by_id(attachment_id)


@router.get("/{attachment_id}/content", response_model=AttachmentContentResponse)
def get_attachment_content(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.get_by_id(attachment_id)


@router.patch("/{attachment_id}", response_model=AttachmentResponse)
def update_attachment(
    attachment_id: UUID,
    request: AttachmentUpdateRequest,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.edit")),
):
    return service.update(attachment_id, request)


@router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.edit")),
):
    service.delete(attachment_id)
    return {"message": "Archivo eliminado correctamente"}
