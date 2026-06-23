# app/api/user/user_repository.py
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Auth, Information, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_users(
        self,
        search: str | None = None,
        email: str | None = None,
        active: bool | None = None,
    ):
        stmt = select(Auth).options(
            selectinload(Auth.profile),
            selectinload(Auth.user_roles_links).selectinload(UserRole.role),
        )

        if email:
            stmt = stmt.where(Auth.email.ilike(f"%{email}%"))

        if active is not None:
            stmt = stmt.where(Auth.active.is_(active))

        if search:
            stmt = stmt.outerjoin(Auth.profile).where(
                or_(
                    Auth.email.ilike(f"%{search}%"),
                    Information.name.ilike(f"%{search}%"),
                    Information.lastname.ilike(f"%{search}%"),
                    Information.document_number.ilike(f"%{search}%"),
                )
            )

        return self.db.execute(stmt).scalars().all()

    def get_user_by_id(self, user_id: UUID):
        stmt = (
            select(Auth)
            .options(
                selectinload(Auth.profile),
                selectinload(Auth.user_roles_links).selectinload(UserRole.role),
            )
            .where(Auth.id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_profile_by_id(self, user_id: UUID):
        return self.db.get(Information, user_id)

    def add_profile(self, profile: Information):
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def exists_by_document(
        self,
        document_type: str,
        document_number: str,
        exclude_user_id: UUID | None = None,
    ) -> bool:
        stmt = select(Information).where(
            Information.document_type == document_type,
            Information.document_number == document_number,
        )

        if exclude_user_id is not None:
            stmt = stmt.where(Information.user_id != exclude_user_id)

        return self.db.execute(stmt).scalar_one_or_none() is not None

    def update_profile(self, profile: Information, data: dict):
        for key, value in data.items():
            setattr(profile, key, value)

        self.db.commit()
        self.db.refresh(profile)

        return profile
