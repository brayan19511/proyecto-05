# app/models/security.py
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_postgres import Base

if TYPE_CHECKING:
    from .user import Information


# -------------------------
# USER - ROLE (M2M)
# -------------------------
class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "security"}

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("security.role.id"), primary_key=True
    )

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now()
    )

    user: Mapped["Auth"] = relationship(back_populates="user_roles_links")
    role: Mapped["Role"] = relationship(back_populates="user_links")


# -------------------------
# USER
# -------------------------
class Auth(Base):
    __tablename__ = "auth"
    __table_args__ = {"schema": "security"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now()
    )

    profile: Mapped["Information"] = relationship(
        back_populates="auth", uselist=False
    )

    user_roles_links: Mapped[List["UserRole"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    @property
    def active_roles(self):
        return [link.role for link in self.user_roles_links if link.active]

    @property
    def permissions(self):
        perms = []
        for role in self.active_roles:
            perms.extend(role.permissions)

        # eliminar duplicados por id
        return list({p.id: p for p in perms}.values())


# -------------------------
# ROLE
# -------------------------
class Role(Base):
    __tablename__ = "role"
    __table_args__ = (
        UniqueConstraint("name", name="uq_role_name"),
        {"schema": "security"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now()
    )

    user_links: Mapped[List["UserRole"]] = relationship(
        back_populates="role", lazy="selectin"
    )

    permission_links: Mapped[List["RolePermission"]] = relationship(
        back_populates="role", lazy="selectin"
    )

    @property
    def permissions(self):
        return [link.permission for link in self.permission_links if link.permission.active]


# -------------------------
# PERMISSION
# -------------------------
class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = (
        UniqueConstraint("code", name="uq_permission_code"),
        {"schema": "security"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String, nullable=False)  
    # ej: "sap.read", "cic.execute"

    description: Mapped[str] = mapped_column(String)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now()
    )


# -------------------------
# ROLE - PERMISSION (M2M)
# -------------------------
class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "security"}

    role_id: Mapped[int] = mapped_column(
        ForeignKey("security.role.id"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("security.permission.id"), primary_key=True
    )

    role: Mapped["Role"] = relationship(back_populates="permission_links")
    permission: Mapped["Permission"] = relationship(lazy="joined")