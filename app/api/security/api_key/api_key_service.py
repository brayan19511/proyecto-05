import hashlib
import secrets

from uuid import uuid4

from fastapi import HTTPException

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

        except Exception as e:
            self.repository.rollback()
            raise HTTPException(
                status_code=500,
                detail=str(e),
            )

    def get_my_keys(self, user_id):
        return self.repository.get_by_user(user_id)

    def deactivate_key(
        self,
        api_key_id,
    ):
        api_key = self.repository.get_by_id(
            api_key_id
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