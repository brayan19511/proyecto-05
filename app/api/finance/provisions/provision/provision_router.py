# app/api/provisions/provision/provision_router.py
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.finance.provisions.provision.provision_schema import (
    ProvisionAccessRequest,
    ProvisionActionRequest,
    ProvisionCreateRequest,
    ProvisionDetailResponse,
    ProvisionDocumentRequest,
    ProvisionDocumentResponse,
    ProvisionDocumentUpdateRequest,
    ProvisionSummaryResponse,
    ProvisionUpdateRequest,
)
from app.api.finance.provisions.access import (
    can_edit_all_provisions,
    can_view_all_provisions,
    resolve_provision_scope,
)
from app.api.finance.provisions.provision.provision_service import ProvisionService
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.core.security import PermissionChecker

router = APIRouter()


def get_service(db: Session = Depends(get_db)):
    return ProvisionService(db)


# Checkers de permisos reutilizando el helper común (bypass de admin incluido).
require_provision_view = require_any_permission(
    "provisions.view",
    "provisions.view_all",
    "provisions.edit",
    "provisions.edit_all",
    "provisions.review",
    detail="No tienes permisos para ver provisiones",
)

require_provision_edit = require_any_permission(
    "provisions.edit",
    "provisions.edit_all",
    "provisions.documents.edit",
    detail="No tienes permisos para editar provisiones",
)

require_provision_access_edit = require_any_permission(
    "provisions.edit",
    "provisions.edit_all",
    "provisions.access.edit",
    detail="No tienes permisos para administrar accesos de provisiones",
)


@router.post("", response_model=ProvisionSummaryResponse)
def create_provision(
    request: ProvisionCreateRequest,
    db: Session = Depends(get_db),
    service: ProvisionService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.create")),
):
    provision = service.create_provision(
        request=request,
        user_id=current_user.id,
        scope=resolve_provision_scope(db, current_user),
    )

    return service.to_summary_response(provision)


@router.get("", response_model=list[ProvisionSummaryResponse])
def get_provisions(
    search: str | None = Query(default=None),
    status_id: int | None = Query(default=None),
    area_id: int | None = Query(default=None),
    company_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_view),
):
    return service.get_provisions(
        search=search,
        status_id=status_id,
        area_id=area_id,
        company_id=company_id,
        user_id=None if can_view_all_provisions(current_user) else current_user.id,
        scope=resolve_provision_scope(db, current_user),
    )


@router.get("/review", response_model=list[ProvisionSummaryResponse])
def get_review_queue(
    area_id: int | None = Query(default=None),
    company_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    service: ProvisionService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.review")),
):
    return service.get_review_queue(
        area_id=area_id,
        company_id=company_id,
        scope=resolve_provision_scope(db, current_user),
    )


@router.get("/documents/{document_id}", response_model=ProvisionDocumentResponse)
def get_document(
    document_id: UUID,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_view),
):
    return service.get_document(
        document_id=document_id,
        user_id=current_user.id,
        can_view_all=can_view_all_provisions(current_user),
    )


@router.patch("/documents/{document_id}", response_model=ProvisionDocumentResponse)
def update_document(
    document_id: UUID,
    request: ProvisionDocumentUpdateRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_edit),
):
    return service.update_document(
        document_id=document_id,
        request=request,
        user_id=current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: UUID,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_edit),
):
    service.delete_document(
        document_id=document_id,
        user_id=current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )

    return {"message": "Documento eliminado correctamente"}


@router.get("/{provision_id}", response_model=ProvisionDetailResponse)
def get_provision(
    provision_id: UUID,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_view),
):
    return service.get_provision(
        provision_id=provision_id,
        user_id=current_user.id,
        can_view_all=can_view_all_provisions(current_user),
    )


@router.put("/{provision_id}", response_model=ProvisionSummaryResponse)
def update_provision(
    provision_id: UUID,
    request: ProvisionUpdateRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_edit),
):
    provision = service.update_provision(
        provision_id=provision_id,
        request=request,
        user_id=current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )

    return service.to_summary_response(provision)


@router.post("/{provision_id}/documents", response_model=ProvisionDocumentResponse)
def add_document(
    provision_id: UUID,
    request: ProvisionDocumentRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_edit),
):
    return service.add_document(
        provision_id=provision_id,
        request=request,
        user_id=current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )


@router.post("/{provision_id}/access")
def grant_access(
    provision_id: UUID,
    request: ProvisionAccessRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_access_edit),
):
    access = service.grant_access(
        provision_id=provision_id,
        request=request,
        user_id=current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )

    return {
        "message": "Acceso registrado correctamente",
        "id": access.id,
    }


@router.post("/{provision_id}/submit", response_model=ProvisionDetailResponse)
def submit_for_review(
    provision_id: UUID,
    request: ProvisionActionRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_edit),
):
    return service.submit_for_review(
        provision_id,
        request,
        current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )


@router.post("/{provision_id}/approve", response_model=ProvisionDetailResponse)
def approve(
    provision_id: UUID,
    request: ProvisionActionRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.review")),
):
    return service.approve(provision_id, request, current_user.id)


@router.post("/{provision_id}/reject-for-edit", response_model=ProvisionDetailResponse)
def reject_for_edit(
    provision_id: UUID,
    request: ProvisionActionRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.review")),
):
    return service.reject_for_edit(provision_id, request, current_user.id)


@router.post("/{provision_id}/reject-final", response_model=ProvisionDetailResponse)
def reject_final(
    provision_id: UUID,
    request: ProvisionActionRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(PermissionChecker("provisions.review")),
):
    return service.reject_final(provision_id, request, current_user.id)


@router.post("/{provision_id}/cancel", response_model=ProvisionDetailResponse)
def cancel(
    provision_id: UUID,
    request: ProvisionActionRequest,
    service: ProvisionService = Depends(get_service),
    current_user=Depends(require_provision_edit),
):
    return service.cancel(
        provision_id,
        request,
        current_user.id,
        can_edit_all=can_edit_all_provisions(current_user),
    )
