from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class AnalyticsIngestionRun(Base, AuditMixin):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("ix_ingestion_runs_source_table_created", "source_code", "table_name", "created_at"),
        Index("ix_ingestion_runs_status_created", "status", "created_at"),
        {"schema": "analytics"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_code: Mapped[str] = mapped_column(String(40), nullable=False)
    table_name: Mapped[str] = mapped_column(String(120), nullable=False)
    table_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="CREATED", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rows_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["AnalyticsIngestionItem"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AnalyticsIngestionItem(Base):
    __tablename__ = "ingestion_items"
    __table_args__ = (
        Index("ix_ingestion_items_run_reference", "run_id", "reference", unique=True),
        Index("ix_ingestion_items_status", "status"),
        {"schema": "analytics"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("analytics.ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(String(160), nullable=False)
    business_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    rows_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[AnalyticsIngestionRun] = relationship(back_populates="items")
