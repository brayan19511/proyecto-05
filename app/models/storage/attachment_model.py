from uuid import UUID, uuid4

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class Attachment(Base, AuditMixin):
    __tablename__ = "attachments"
    __table_args__ = (
        Index(
            "ix_attachments_entity_type_entity_id",
            "entity_type",
            "entity_id",
        ),
        {"schema": "storage"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
