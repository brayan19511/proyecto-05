# app/api/security/user_scope/user_scope_router.py

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.security.user_scope.user_scope_schema import (
    UserAreaAccessRequest,
    UserAreaAccessResponse,
    UserScopeReplaceRequest,
    UserScopeResponse,
)
from app.api.security.user_scope.user_scope_service import UserScopeService
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.core.security import get_current_user
from app.core.exceptions import get_or_404

router = APIRouter(prefix="/user-areas", tags=["ACCESOS POR AREA"])


def get_service(db: Session = Depends(get_db)) -> UserScopeService:
    return UserScopeService(db)


require_scope_view = require_any_permission(
    "security.users.view",
    "security.users.edit",
    "security.roles.edit",
    detail="No tienes permisos para ver los accesos por area",
)

require_scope_edit = require_any_permission(
    "security.users.edit",
    "security.roles.edit",
    detail="No tienes permisos para gestionar los accesos por area",
)


@router.get("", response_model=list[UserAreaAccessResponse])
def get_accesses(
    user_id: UUID | None = Query(default=None),
    company_id: int | None = Query(default=None),
    area_id: int | None = Query(default=None),
    # active=None trae activos e inactivos.
    active: bool | None = Query(default=True),
    service: UserScopeService = Depends(get_service),
    current_user=Depends(require_scope_view),
):
    """Lista accesos. Sirve tanto para "que ve un usuario" como para
    "quienes estan en esta area"."""
    return service.get_accesses(
        user_id=user_id,
        company_id=company_id,
        area_id=area_id,
        active=active,
    )


@router.get("/me", response_model=UserScopeResponse)
def get_my_scope(
    service: UserScopeService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    """Alcance del usuario autenticado (no requiere permisos de seguridad)."""
    return service.get_user_scope_detail(current_user)


@router.get("/{user_id}", response_model=UserScopeResponse)
def get_user_scope(
    user_id: UUID,
    service: UserScopeService = Depends(get_service),
    current_user=Depends(require_scope_view),
):
    """Alcance del usuario agrupado como empresa > areas."""
    user = get_or_404(
        service.auth_repository.get_by_id(user_id),
        "El usuario indicado no existe",
    )

    return service.get_user_scope_detail(user)


@router.post("", response_model=UserAreaAccessResponse)
def assign_access(
    request: UserAreaAccessRequest,
    service: UserScopeService = Depends(get_service),
    current_user=Depends(require_scope_edit),
):
    """Asigna un area (o la empresa completa si area_id es null)."""
    return service.assign_access(request, current_user.id)


@router.put("/{user_id}", response_model=UserScopeResponse)
def replace_user_scope(
    user_id: UUID,
    request: UserScopeReplaceRequest,
    service: UserScopeService = Depends(get_service),
    current_user=Depends(require_scope_edit),
):
    """Reemplaza el alcance completo del usuario (lo que sale se desactiva)."""
    return service.replace_user_scope(user_id, request.items, current_user.id)


@router.post("/{access_id}/deactivate", response_model=UserAreaAccessResponse)
def deactivate_access(
    access_id: int,
    service: UserScopeService = Depends(get_service),
    current_user=Depends(require_scope_edit),
):
    return service.set_access_active(access_id, False, current_user.id)


@router.post("/{access_id}/activate", response_model=UserAreaAccessResponse)
def activate_access(
    access_id: int,
    service: UserScopeService = Depends(get_service),
    current_user=Depends(require_scope_edit),
):
    return service.set_access_active(access_id, True, current_user.id)
