# app/api/user/user_repository.py
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import UUID, select
from app.models.security import Auth
from app.models.user import Information

class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    def get_users(self):
        # Usamos selectinload para traer la relación 'profile' de una vez
        stmt = select(Auth).options(selectinload(Auth.profile))
        return self.db.execute(stmt).scalars().all()

    def get_user_by_id(self, user_id: UUID): # Cambiar int por UUID
        return self.db.get(Auth, user_id)

    def get_profile_by_id(self, user_id: UUID): # Cambiar str por UUID
        return self.db.get(Information, user_id)
    def add_profile(self, profile: Information):
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    def exists_by_document(self, document_type: str, document_number: str) -> bool:
        stmt = select(Information).where(
            Information.document_type == document_type,
            Information.document_number == document_number
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def update_profile(self, profile: Information, data: dict):
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
        self.db.commit()
        return profile