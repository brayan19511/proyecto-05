# app\api\security\api_key\api_key_repository.py

from uuid import UUID
from sqlalchemy.orm import Session
from app.models.auth.security_model import ApiKey


class ApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, api_key: ApiKey):
        self.db.add(api_key)
        return api_key

    def get_by_id(self, api_key_id: UUID):
        return self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()

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

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
