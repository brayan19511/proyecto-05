from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=True,
    )
