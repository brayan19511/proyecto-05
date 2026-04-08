from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import Information

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_profile_by_id(self, user_id: str) -> Information | None:
        return self.db.get(Information, user_id)
    def exists_by_document(self, document_type: str, document_number: str) -> bool:
        stmt = select(Information).where(
            Information.document_number == document_number
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def update_profile(self, profile: Information, data: dict):
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
        self.db.commit()
        return profile