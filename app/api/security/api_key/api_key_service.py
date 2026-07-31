import hashlib
import secrets

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.db.integrity import raise_integrity_error
from app.models.auth.security_model import ApiKey
from app.api.security.api_key.api_key_repository import ApiKeyRepository


class ApiKeyService:

    def __init__(self, db):
        self.repository = ApiKeyRepository(db)

    def create_api_key(
        self,
        user_id,
        name,
        expires_at=None,
    ):
        try:

            # esta es la llave que verá el usuario
            raw_api_key = (
                f"cb_live_{secrets.token_urlsafe(48)}"
            )

            key_hash = hashlib.sha256(
                raw_api_key.encode()
            ).hexdigest()

            api_key = ApiKey(
                id=uuid4(),
                user_id=user_id,
                name=name,
                key_hash=key_hash,
                active=True,
                expires_at=expires_at,
            )

            self.repository.create(api_key)
            self.repository.commit()

            return {
                "api_key": raw_api_key,
                "key_info": api_key,
            }

        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                invalid_references={
                    "api_key_user_id_fkey": "El usuario indicado no existe"
                },
                default_message="No se pudo crear la API Key",
            )
        except Exception as exc:
            self.repository.rollback()
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear la API Key",
            ) from exc

    @staticmethod
    def _generate_raw_api_key() -> str:
        return f"cb_live_{secrets.token_urlsafe(48)}"

    @staticmethod
    def _hash_api_key(raw_api_key: str) -> str:
        return hashlib.sha256(raw_api_key.encode()).hexdigest()

    def get_my_keys(self, user_id):
        return self.repository.get_by_user(user_id)

    def update_key(
        self,
        *,
        api_key_id,
        user_id,
        data: dict,
    ):
        api_key = self.repository.get_by_id_and_user(api_key_id, user_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API Key no encontrada")

        if "name" in data:
            api_key.name = data["name"]
        if "expires_at" in data:
            api_key.expires_at = data["expires_at"]
        if "active" in data:
            api_key.active = data["active"]

        self.repository.commit()
        return api_key

    def rotate_key(self, *, api_key_id, user_id):
        api_key = self.repository.get_by_id_and_user(api_key_id, user_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API Key no encontrada")

        raw_api_key = self._generate_raw_api_key()
        api_key.key_hash = self._hash_api_key(raw_api_key)
        api_key.active = True
        self.repository.commit()

        return {
            "api_key": raw_api_key,
            "key_info": api_key,
        }

    def deactivate_key(
        self,
        api_key_id,
        user_id,
    ):
        api_key = self.repository.get_by_id_and_user(
            api_key_id,
            user_id,
        )

        if not api_key:
            raise HTTPException(
                status_code=404,
                detail="API Key no encontrada"
            )

        api_key.active = False

        self.repository.commit()

        return {
            "message": "API Key desactivada"
        }
