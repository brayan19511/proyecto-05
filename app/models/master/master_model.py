from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class Company(Base, AuditMixin):
    __tablename__ = "companies"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rut: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Currency(Base, AuditMixin):
    __tablename__ = "currencies"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange_rate_to_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        default=Decimal("1"),
        nullable=False,
    )
    is_base_currency: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Area(Base, AuditMixin):
    __tablename__ = "areas"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
