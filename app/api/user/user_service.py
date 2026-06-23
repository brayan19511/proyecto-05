from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Information
from .user_repository import UserRepository
from .user_schemas import UserProfileCreate, UserProfileUpdate


class UserService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def _to_user_response(self, user):
        profile = user.profile
        active_role_links = [
            link
            for link in user.user_roles_links
            if link.active and link.role and link.role.active
        ]

        return {
            "user_id": user.id,
            "email": user.email,
            "active": user.active,
            "name": profile.name if profile else None,
            "lastname": profile.lastname if profile else None,
            "phone": profile.phone if profile else None,
            "birthday": profile.birthday if profile else None,
            "document_type": profile.document_type if profile else None,
            "document_number": profile.document_number if profile else None,
            "role_ids": [link.role_id for link in active_role_links],
            "roles": [link.role.name for link in active_role_links],
        }

    def get_users(
        self,
        search: str | None = None,
        email: str | None = None,
        active: bool | None = None,
    ):
        users = self.repository.get_users(
            search=search,
            email=email,
            active=active,
        )
        return [self._to_user_response(user) for user in users]

    def get_user_profile(self, user_id: UUID):
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return self._to_user_response(user)

    def create_user_profile(self, user_id: UUID, data: UserProfileCreate):
        profile = self.repository.get_profile_by_id(user_id)
        self._validate_document(user_id, data)

        if profile:
            update_data = data.model_dump(exclude_unset=True)
            self.repository.update_profile(profile, update_data)
        else:
            new_profile = Information(
                user_id=user_id,
                **data.model_dump(),
            )
            self.repository.add_profile(new_profile)

        return self.get_user_profile(user_id)

    def update_profile(self, user_id: UUID, data: UserProfileUpdate):
        profile = self.repository.get_profile_by_id(user_id)
        self._validate_document(user_id, data)

        if not profile:
            new_profile = Information(
                user_id=user_id,
                **data.model_dump(),
            )
            self.repository.add_profile(new_profile)
            return self.get_user_profile(user_id)

        try:
            update_data = data.model_dump(exclude_unset=True)
            self.repository.update_profile(profile, update_data)
            return self.get_user_profile(user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def ensure_empty_profile(self, user_id: UUID):
        if self.repository.get_profile_by_id(user_id):
            return

        self.repository.add_profile(Information(user_id=user_id))

    def _validate_document(
        self,
        user_id: UUID,
        data: UserProfileCreate | UserProfileUpdate,
    ):
        if not data.document_number:
            return

        if self.repository.exists_by_document(
            data.document_type,
            data.document_number,
            exclude_user_id=user_id,
        ):
            raise HTTPException(
                status_code=400,
                detail="Documento ya registrado en otro perfil",
            )
