from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiClient, Auth


class ApiClientRepository:
    """Database access without business authorization decisions."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, client_id: UUID) -> ApiClient | None:
        return self.db.get(ApiClient, client_id)

    def get_by_prefix(self, key_prefix: str) -> ApiClient | None:
        return self.db.scalar(
            select(ApiClient).where(ApiClient.key_prefix == key_prefix)
        )

    def get_user(self, user_id: UUID) -> Auth | None:
        return self.db.get(Auth, user_id)

    def list_by_user(self, user_id: UUID) -> list[ApiClient]:
        statement = (
            select(ApiClient)
            .where(ApiClient.user_id == user_id)
            .order_by(ApiClient.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def add(self, client: ApiClient) -> None:
        self.db.add(client)

    def save(self, client: ApiClient) -> ApiClient:
        self.db.commit()
        self.db.refresh(client)
        return client

    def rollback(self) -> None:
        self.db.rollback()
