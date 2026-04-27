# app/api/security/auth/auth_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import UUID, func, select
from app.models.security import Auth, Role, UserRole
from app.models.user import Information


class AuthRepository:
    def __init__(self, db:Session):
        self.db = db
    def create_auth(self, auth_obj: Auth) -> Auth:
        self.db.add(auth_obj)
        return auth_obj
    def get_by_email(self, email)-> Auth | None:
        query=select(Auth).where(Auth.email == email)
        return self.db.execute(query).scalar_one_or_none()
    def get_by_id(self, user_id: str) -> Auth | None:
        query = select(Auth).where(Auth.id == user_id)
        return self.db.execute(query).scalar_one_or_none()
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()