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

    def create_info(self, info_obj: Information) -> Information:
        self.db.add(info_obj)
        return info_obj
    def set_user_status(self, user_id: UUID, status: bool):
        user = self.get_by_id(user_id)
        if user:
            user.active = status
            user.updated_at = func.now()
        return user
    def update_password(self, user_id: UUID, new_password_hash: str) -> bool:
        user=self.get_by_id(user_id)
        if user:
            user.password_hash = new_password_hash
            user.updated_at = func.now()
            self.db.commit()
            return True
        return False

    def get_by_email(self, email)-> Auth | None:
        query=select(Auth).where(Auth.email == email)
        return self.db.execute(query).scalar_one_or_none()
    def get_by_id(self, user_id: str) -> Auth | None:
        query = select(Auth).where(Auth.id == user_id)
        return self.db.execute(query).scalar_one_or_none()
    def get_role_by_id(self, role_id: int) -> Role | None:
        return self.db.get(Role, role_id)
    def assign_role_to_user(self, user: Auth, role: Role):
        link = self.db.query(UserRole).filter_by(
            user_id=user.id, 
            role_id=role.id
        ).first()
        if not link:
            # Si no existe, creamos el nuevo registro en la intermedia
            new_link = UserRole(user_id=user.id, role_id=role.id, active=True)
            self.db.add(new_link)
        else:
            # Si existía pero estaba inactivo, lo activamos
            link.active = True
    def update_role_to_user(self, user: Auth, role: Role,status:bool):
        link = self.db.query(UserRole).filter_by(
            user_id=user.id, 
            role_id=role.id
        ).first()
        if not link:
            # Si no existe, creamos el nuevo registro en la intermedia
            new_link = UserRole(user_id=user.id, role_id=role.id, active=True)
            self.db.add(new_link)
        else:
            # Si existía pero estaba inactivo, lo activamos
            link.active = status
            
    def set_user_role_status(self, user_id: UUID, role_id: int, status: bool):
        # Buscamos la relación en la tabla intermedia
        link = self.db.query(UserRole).filter_by(
            user_id=user_id, 
            role_id=role_id
        ).first()
        
        if link:
            link.active = status
            # updated_at se dispara solo si usaste 'onupdate' en el modelo
        return link
        
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()