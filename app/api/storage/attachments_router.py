from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.storage.attachments_schema import (
    AttachmentCreateRequest,
    AttachmentContentResponse,
    AttachmentResponse,
    AttachmentUpdateRequest,
)
from app.api.storage.attachments_service import AttachmentService
from app.core.db.db_postgres import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/storage/attachments", tags=["Attachments"])


def get_service(db=Depends(get_db)):
    return AttachmentService(db)


def get_permission_codes(user) -> set[str]:
    return {permission.code for permission in user.permissions}


def get_role_names(user) -> set[str]:
    return {
        link.role.name
        for link in user.user_roles_links
        if link.active
    }


def require_any_permission(*permission_codes: str):
    def checker(current_user=Depends(get_current_user)):
        if "Admin" in get_role_names(current_user):
            return current_user

        if get_permission_codes(current_user).intersection(permission_codes):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes permisos suficientes: {', '.join(permission_codes)}",
        )

    return checker


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


@router.post("", response_model=AttachmentResponse)
def create_attachment(
    request: AttachmentCreateRequest,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(
        require_any_permission("provisions.edit", "provisions.documents.edit"),
    ),
):
    return service.create(request, current_user.id)


@router.patch("/{attachment_id}", response_model=AttachmentResponse)
def update_attachment(
    attachment_id: UUID,
    request: AttachmentUpdateRequest,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(
        require_any_permission("provisions.edit", "provisions.documents.edit"),
    ),
):
    return service.update(attachment_id, request)


@router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: UUID,
    service: AttachmentService = Depends(get_service),
    current_user=Depends(
        require_any_permission("provisions.edit", "provisions.documents.edit"),
    ),
):
    service.delete(attachment_id)
    return {"message": "Archivo eliminado correctamente"}
