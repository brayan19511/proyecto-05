from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    func,
    UniqueConstraint,
    Numeric,
)
class AuditMixin:
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=True
    )

    updated_by: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=True
    )