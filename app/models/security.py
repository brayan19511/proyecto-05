from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db_postgres import Base

# Evita importación circular con Pylance
if TYPE_CHECKING:
    from .user import Information

class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "security"}

    user_id: Mapped[UUID] = mapped_column(ForeignKey("security.auth.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("security.role.id"), primary_key=True)
    
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    # Relaciones directas
    user: Mapped["Auth"] = relationship(back_populates="user_roles_links")
    role: Mapped["Role"] = relationship(back_populates="user_links")

class Auth(Base):
    __tablename__ = "auth"
    __table_args__ = {"schema": "security"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    # Relación 1:1 con Perfil (Esquema user)
    profile: Mapped["Information"] = relationship(back_populates="auth", uselist=False)
    
    # Relación hacia la tabla intermedia
    user_roles_links: Mapped[List["UserRole"]] = relationship(back_populates="user")

    # Propiedad para obtener solo roles activos (muy útil para el JWT)
    @property
    def active_roles(self):
        return [link.role for link in self.user_roles_links if link.active]

class Role(Base):
    __tablename__ = "role"
    __table_args__ = {"schema": "security"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    system_name: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    user_links: Mapped[List["UserRole"]] = relationship(back_populates="role")