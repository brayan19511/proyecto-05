from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.storage.attachments_schema import (
    AttachmentCreateRequest,
    AttachmentContentResponse,
    AttachmentResponse,
    AttachmentUpdateRequest,
)
from app.api.storage.attachments_service import AttachmentService
from app.api.finance.provisions.access import (
    can_edit_all_provisions,
    can_view_all_provisions,
)
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/storage/attachments", tags=["ARCHIVOS"])


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
        user_id=current_user.id,
        can_view_all=can_view_all_provisions(current_user),
    )


@router.get("/{attachment_id}", response_model=AttachmentResponse)
def get_attachment(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.get_by_id(
        attachment_id,
        current_user.id,
        can_view_all=can_view_all_provisions(current_user),
    )


@router.get("/{attachment_id}/content", response_model=AttachmentContentResponse)
def get_attachment_content(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.get_by_id(
        attachment_id,
        current_user.id,
        can_view_all=can_view_all_provisions(current_user),
    )


@router.post("", response_model=AttachmentResponse)
def create_attachment(
    request: AttachmentCreateRequest,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(
        require_any_permission("provisions.edit", "provisions.documents.edit"),
    ),
):
    return service.create(
        request,
        current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )


@router.patch("/{attachment_id}", response_model=AttachmentResponse)
def update_attachment(
    attachment_id: UUID,
    request: AttachmentUpdateRequest,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(
        require_any_permission("provisions.edit", "provisions.documents.edit"),
    ),
):
    return service.update(
        attachment_id,
        request,
        current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )


@router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(
        require_any_permission("provisions.edit", "provisions.documents.edit"),
    ),
):
    service.delete(
        attachment_id,
        current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )
    return {"message": "Archivo eliminado correctamente"}
