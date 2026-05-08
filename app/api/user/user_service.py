# app/api/user/user_service.py
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import Information
from .user_repository import UserRepository
from .user_schemas import UserProfileUpdate

class UserService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
    def get_user_profile(self, user_id: UUID):
        profile = self.repository.get_profile_by_id(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")
        return profile
    def create_user_profile(self, user_id: UUID, data):
        # Validar si ya tiene un perfil para no duplicar
        if self.repository.get_profile_by_id(user_id):
            raise HTTPException(status_code=400, detail="El usuario ya tiene un perfil creado")
        if data.document_number:
            if self.repository.exists_by_document(data.document_type, data.document_number):
                raise HTTPException(status_code=400, detail="Documento ya registrado en otro perfil")
            
        new_profile = Information(
                        user_id=user_id,
                        **data.model_dump()
                        )
        return self.repository.add_profile(new_profile)
    
    def update_profile(self, user_id: UUID, data: UserProfileUpdate):
        profile = self.repository.get_profile_by_id(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")
        if data.document_number and data.document_number != profile.document_number:
            if self.repository.exists_by_document(data.document_type, data.document_number):
                raise HTTPException(status_code=400, detail="Documento ya registrado en otro perfil")
        # Convertimos el schema a dict excluyendo lo que no se envió
        try:
            update_data = data.model_dump(exclude_unset=True)
            return self.repository.update_profile(profile, update_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))