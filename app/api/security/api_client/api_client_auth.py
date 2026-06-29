"""Authentication dependency shared by every analytics endpoint."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.security.api_client.api_client_service import ApiClientService
from app.core.db.db_postgres import get_db
from app.core.security import get_user_from_token


optional_bearer = OAuth2PasswordBearer(
    tokenUrl="/api/security/auth/login",
    auto_error=False,
)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class AnalyticsPrincipal:
    auth_type: str
    subject_id: UUID


def require_analytics_access(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_bearer),
    api_key: str | None = Depends(api_key_header),
) -> AnalyticsPrincipal:
    """Accept a scoped integration key or an authorized frontend JWT."""
    if api_key:
        client = ApiClientService(db).authenticate(
            raw_key=api_key,
            required_scope="analytics.read",
        )
        request.state.user_id = client.user_id
        request.state.api_client_id = client.id
        request.state.auth_type = "api_key"
        return AnalyticsPrincipal("api_key", client.id)

    if token:
        user = get_user_from_token(token=token, db=db, request=request)
        roles = {role.name for role in user.active_roles}
        permissions = {permission.code for permission in user.permissions}
        if "Admin" not in roles and "analytics.read" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para consultar analytics.",
            )
        return AnalyticsPrincipal("jwt", user.id)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Debe enviar un Bearer token o X-API-Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )
