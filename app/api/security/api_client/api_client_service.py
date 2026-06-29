from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.security.api_client.api_client_repository import (
    ApiClientRepository,
)
from app.api.security.api_client.api_client_schemas import (
    ApiClientCreate,
    ApiClientUpdate,
)
from app.models import ApiClient, Auth


ALLOWED_SCOPES = {"analytics.read"}
LAST_USED_WRITE_INTERVAL = timedelta(minutes=15)


class ApiClientService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ApiClientRepository(db)

    def create(self, data: ApiClientCreate, current_user: Auth) -> tuple[ApiClient, str]:
        owner_id = data.user_id or current_user.id
        if owner_id != current_user.id and not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un administrador puede asignar claves a otro usuario.",
            )

        owner = self._get_active_user(owner_id)
        if not self._has_analytics_access(owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El propietario no tiene el permiso analytics.read.",
            )
        scopes = self._validate_scopes(data.scopes)
        self._validate_expiration(data.expires_at)
        raw_key, prefix, key_hash = self._generate_key()

        client = ApiClient(
            user_id=owner.id,
            name=data.name.strip(),
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=data.expires_at,
            active=True,
        )
        self.repository.add(client)
        return self.repository.save(client), raw_key

    def list_clients(self, current_user: Auth, user_id: UUID | None = None):
        target_id = user_id or current_user.id
        if target_id != current_user.id and not self._is_admin(current_user):
            raise HTTPException(status_code=403, detail="Acceso denegado.")
        return self.repository.list_by_user(target_id)

    def update(
        self,
        client_id: UUID,
        data: ApiClientUpdate,
        current_user: Auth,
    ) -> ApiClient:
        client = self._get_authorized_client(client_id, current_user)
        fields = data.model_fields_set

        if "name" in fields and data.name is not None:
            client.name = data.name.strip()
        if "scopes" in fields and data.scopes is not None:
            client.scopes = self._validate_scopes(data.scopes)
        if "expires_at" in fields:
            self._validate_expiration(data.expires_at)
            client.expires_at = data.expires_at

        return self.repository.save(client)

    def assign(
        self,
        client_id: UUID,
        user_id: UUID,
        current_user: Auth,
    ) -> ApiClient:
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un administrador puede reasignar una clave.",
            )
        client = self._get_client(client_id)
        owner = self._get_active_user(user_id)
        if not self._has_analytics_access(owner):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nuevo propietario no tiene analytics.read.",
            )
        client.user_id = owner.id
        return self.repository.save(client)

    def set_active(
        self,
        client_id: UUID,
        active: bool,
        current_user: Auth,
    ) -> ApiClient:
        client = self._get_authorized_client(client_id, current_user)
        if active and client.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Una clave revocada debe rotarse; no puede reactivarse.",
            )
        if active and self._is_expired(client):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Actualice la fecha de expiracion antes de activar la clave.",
            )
        client.active = active
        return self.repository.save(client)

    def rotate(
        self,
        client_id: UUID,
        current_user: Auth,
    ) -> tuple[ApiClient, str]:
        client = self._get_authorized_client(client_id, current_user)
        if self._is_expired(client):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Actualice la fecha de expiracion antes de rotar la clave.",
            )
        raw_key, prefix, key_hash = self._generate_key()
        client.key_prefix = prefix
        client.key_hash = key_hash
        client.active = True
        client.revoked_at = None
        client.last_used_at = None
        return self.repository.save(client), raw_key

    def revoke(self, client_id: UUID, current_user: Auth) -> ApiClient:
        client = self._get_authorized_client(client_id, current_user)
        client.active = False
        client.revoked_at = datetime.now(timezone.utc)
        return self.repository.save(client)

    def authenticate(self, raw_key: str, required_scope: str) -> ApiClient:
        prefix = self._extract_prefix(raw_key)
        client = self.repository.get_by_prefix(prefix)
        invalid = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida o inactiva.",
        )

        if client is None:
            raise invalid
        if not secrets.compare_digest(client.key_hash, self._hash_key(raw_key)):
            raise invalid
        if not client.active or client.revoked_at is not None:
            raise invalid
        if self._is_expired(client):
            raise invalid
        if required_scope not in client.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"La API key no tiene el scope {required_scope}.",
            )

        owner = self.repository.get_user(client.user_id)
        if (
            owner is None
            or not owner.active
            or not self._has_analytics_access(owner)
        ):
            raise invalid

        self._touch_last_used(client)
        return client

    def _touch_last_used(self, client: ApiClient) -> None:
        now = datetime.now(timezone.utc)
        last_used = client.last_used_at
        if last_used is not None and last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=timezone.utc)

        # Throttling this write prevents every dashboard query from becoming
        # an additional UPDATE on a small cloud database.
        if last_used is None or now - last_used >= LAST_USED_WRITE_INTERVAL:
            client.last_used_at = now
            self.repository.save(client)

    def _generate_key(self) -> tuple[str, str, str]:
        for _ in range(5):
            prefix = secrets.token_hex(8)
            if self.repository.get_by_prefix(prefix) is None:
                raw_key = f"rsk_{prefix}.{secrets.token_urlsafe(32)}"
                return raw_key, prefix, self._hash_key(raw_key)
        raise RuntimeError("No se pudo generar un prefijo de API key unico.")

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_prefix(raw_key: str) -> str:
        if not raw_key.startswith("rsk_") or "." not in raw_key:
            return ""
        return raw_key[4:].split(".", maxsplit=1)[0]

    @staticmethod
    def _validate_scopes(scopes: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(scope.strip() for scope in scopes if scope.strip()))
        invalid = set(normalized) - ALLOWED_SCOPES
        if not normalized or invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scopes invalidos: {sorted(invalid)}.",
            )
        return normalized

    @staticmethod
    def _validate_expiration(expires_at: datetime | None) -> None:
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La expiracion debe ser una fecha futura.",
            )

    @staticmethod
    def _is_admin(user: Auth) -> bool:
        return any(role.name == "Admin" for role in user.active_roles)

    @classmethod
    def _has_analytics_access(cls, user: Auth) -> bool:
        if cls._is_admin(user):
            return True
        return any(
            permission.code == "analytics.read"
            for permission in user.permissions
        )

    @staticmethod
    def _is_expired(client: ApiClient) -> bool:
        if client.expires_at is None:
            return False
        expires_at = client.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)

    def _get_active_user(self, user_id: UUID) -> Auth:
        user = self.repository.get_user(user_id)
        if user is None or not user.active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario activo no encontrado.",
            )
        return user

    def _get_client(self, client_id: UUID) -> ApiClient:
        client = self.repository.get(client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API client no encontrado.",
            )
        return client

    def _get_authorized_client(
        self,
        client_id: UUID,
        current_user: Auth,
    ) -> ApiClient:
        client = self._get_client(client_id)
        if client.user_id != current_user.id and not self._is_admin(current_user):
            raise HTTPException(status_code=403, detail="Acceso denegado.")
        return client
