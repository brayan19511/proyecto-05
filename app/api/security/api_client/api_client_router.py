from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.security.api_client.api_client_schemas import (
    ApiClientAssign,
    ApiClientCreate,
    ApiClientResponse,
    ApiClientSecretResponse,
    ApiClientStatusUpdate,
    ApiClientUpdate,
)
from app.api.security.api_client.api_client_service import ApiClientService
from app.core.db.db_postgres import get_db
from app.core.security import get_current_user


router = APIRouter(prefix="/api-clients", tags=["API Clients"])


def _secret_response(client, raw_key: str) -> ApiClientSecretResponse:
    public_data = ApiClientResponse.model_validate(client).model_dump()
    return ApiClientSecretResponse(**public_data, api_key=raw_key)


@router.get("", response_model=list[ApiClientResponse])
def list_api_clients(
    user_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ApiClientService(db).list_clients(current_user, user_id)


@router.post(
    "",
    response_model=ApiClientSecretResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_client(
    data: ApiClientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client, raw_key = ApiClientService(db).create(data, current_user)
    return _secret_response(client, raw_key)


@router.patch("/{client_id}", response_model=ApiClientResponse)
def update_api_client(
    client_id: UUID,
    data: ApiClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ApiClientService(db).update(client_id, data, current_user)


@router.put("/{client_id}/status", response_model=ApiClientResponse)
def set_api_client_status(
    client_id: UUID,
    data: ApiClientStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ApiClientService(db).set_active(
        client_id,
        data.active,
        current_user,
    )


@router.put("/{client_id}/assign", response_model=ApiClientResponse)
def assign_api_client(
    client_id: UUID,
    data: ApiClientAssign,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ApiClientService(db).assign(client_id, data.user_id, current_user)


@router.post("/{client_id}/rotate", response_model=ApiClientSecretResponse)
def rotate_api_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client, raw_key = ApiClientService(db).rotate(client_id, current_user)
    return _secret_response(client, raw_key)


@router.delete("/{client_id}", response_model=ApiClientResponse)
def revoke_api_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ApiClientService(db).revoke(client_id, current_user)
