# app\api\security\api_key\api_key_repository.py

from uuid import UUID

from app.core.db.base_repository import BaseRepository
from app.models.auth.security_model import ApiKey


class ApiKeyRepository(BaseRepository[ApiKey]):
    model = ApiKey

    def create(self, api_key: ApiKey):
        return self.add(api_key)

    def get_by_id_and_user(self, api_key_id: UUID, user_id: UUID):
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
            .first()
        )

    def get_by_hash(self, key_hash: str):
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.active == True)
            .first()
        )

    def get_by_user(self, user_id: UUID):
        return self.db.query(ApiKey).filter(ApiKey.user_id == user_id).all()
