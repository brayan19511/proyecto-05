from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.core.db.db_postgres import get_db
from app.core.security import get_current_user

from app.api.security.api_key.api_key_service import (
    ApiKeyService,
)

from app.api.security.api_key.api_key_schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeyUpdateRequest,
)

router = APIRouter(
    prefix="/api-key",
    tags=["API KEYS"],
)

@router.post(
    "",
    response_model=ApiKeyCreatedResponse
)
def create_api_key(
    data: ApiKeyCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ApiKeyService(db)

    return service.create_api_key(
        user_id=current_user.id,
        name=data.name,
        expires_at=data.expires_at,
    )
@router.get(
    "",
    response_model=list[ApiKeyResponse]
)
def get_my_keys(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ApiKeyService(db)

    return service.get_my_keys(
        current_user.id
    )


@router.patch(
    "/{api_key_id}",
    response_model=ApiKeyResponse
)
def update_key(
    api_key_id: UUID,
    data: ApiKeyUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ApiKeyService(db)

    return service.update_key(
        api_key_id=api_key_id,
        user_id=current_user.id,
        data=data.model_dump(exclude_unset=True),
    )


@router.post(
    "/{api_key_id}/rotate",
    response_model=ApiKeyCreatedResponse
)
def rotate_key(
    api_key_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ApiKeyService(db)

    return service.rotate_key(
        api_key_id=api_key_id,
        user_id=current_user.id,
    )


@router.delete("/{api_key_id}")
def deactivate_key(
    api_key_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ApiKeyService(db)

    return service.deactivate_key(
        api_key_id,
        current_user.id,
    )
