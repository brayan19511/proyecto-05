# app/models/security.py
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4


from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    func,
    text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin

if TYPE_CHECKING:
    from app.models.master.master_model import Area, Company

    from .user_model import Information


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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
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

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now()
    )

    profile: Mapped["Information"] = relationship(back_populates="auth", uselist=False)

    user_roles_links: Mapped[List["UserRole"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    area_access_links: Mapped[List["UserAreaAccess"]] = relationship(
        back_populates="user",
        foreign_keys="UserAreaAccess.user_id",
        lazy="selectin",
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

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
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
        return [
            link.permission for link in self.permission_links if link.permission.active
        ]


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

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
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


# -------------------------
# USER - COMPANY / AREA (ALCANCE OPERATIVO)
# -------------------------
class UserAreaAccess(Base, AuditMixin):
    """Alcance operativo de un usuario: en que area de que empresa puede trabajar.

    Una fila = "este usuario opera en el area X de la empresa Y".
    Si ``area_id`` es NULL la fila significa "todas las areas de esa empresa"
    (util para gerentes o para operaciones de una sola empresa, como Peru).

    El catalogo de areas se mantiene global (master.areas): el amarre con la
    empresa vive aqui, para no duplicar el catalogo por cada sociedad.
    """

    __tablename__ = "user_area_access"
    __table_args__ = (
        # En Postgres los NULL no colisionan en un UNIQUE normal, por eso se
        # usan dos indices parciales en lugar de un UniqueConstraint simple.
        Index(
            "uq_user_area_access_area",
            "user_id",
            "company_id",
            "area_id",
            unique=True,
            postgresql_where=text("area_id IS NOT NULL"),
        ),
        Index(
            "uq_user_area_access_company",
            "user_id",
            "company_id",
            unique=True,
            postgresql_where=text("area_id IS NULL"),
        ),
        Index("ix_user_area_access_user", "user_id"),
        Index("ix_user_area_access_company_area", "company_id", "area_id"),
        {"schema": "security"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("master.companies.id"),
        nullable=False,
    )

    # NULL = todas las areas de la empresa.
    area_id: Mapped[int | None] = mapped_column(
        ForeignKey("master.areas.id"),
        nullable=True,
    )

    # Borrado logico: estos accesos nunca se eliminan, se desactivan.
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )

    user: Mapped["Auth"] = relationship(
        back_populates="area_access_links",
        foreign_keys=[user_id],
    )

    company: Mapped["Company"] = relationship(lazy="joined")

    area: Mapped["Area | None"] = relationship(lazy="joined")

    @property
    def company_code(self) -> str | None:
        return self.company.code if self.company else None

    @property
    def company_name(self) -> str | None:
        return self.company.name if self.company else None

    @property
    def area_code(self) -> str | None:
        return self.area.code if self.area else None

    @property
    def area_name(self) -> str | None:
        return self.area.name if self.area else None


class ApiKey(Base, AuditMixin):
    __tablename__ = "api_key"
    __table_args__ = {"schema": "security"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String)

    key_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["Auth"] = relationship(foreign_keys=[user_id])
