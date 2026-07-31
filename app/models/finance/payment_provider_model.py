from uuid import UUID, uuid4

from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class PaymentProvider(Base, AuditMixin):
    """Proveedor reutilizable para pagos y futuros flujos relacionados."""

    __tablename__ = "payment_providers"
    __table_args__ = (
        UniqueConstraint("tax_id", name="uq_payment_provider_tax_id"),
        Index("ix_payment_provider_legal_name", "legal_name"),
        {"schema": "finance"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tax_id: Mapped[str] = mapped_column(String(20), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    commercial_names: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    normalized_names: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    emails_payments: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
