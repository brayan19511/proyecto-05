from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.jobs.constants import (
    JobBatchStatus,
    JobItemStatus,
    JobStatus,
    JobTriggerSource,
    ScheduledJobScheduleKind,
)
from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin

if TYPE_CHECKING:
    from app.models.auth.security_model import Auth


def _enum_values(enum_class) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_class)


class Job(Base, AuditMixin):
    """User-visible asynchronous operation and its aggregate progress."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_enum_values(JobStatus)})",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            f"trigger_source IN ({_enum_values(JobTriggerSource)})",
            name="ck_jobs_trigger_source",
        ),
        UniqueConstraint(
            "created_by",
            "job_type",
            "idempotency_key",
            name="uq_jobs_creator_type_idempotency",
        ),
        Index("ix_jobs_created_by_created_at", "created_by", "created_at"),
        Index("ix_jobs_job_type", "job_type"),
        Index("ix_jobs_parent_job_id", "parent_job_id"),
        Index("ix_jobs_scheduled_job_id", "scheduled_job_id"),
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_trigger_source_created_at", "trigger_source", "created_at"),
        {"schema": "jobs"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.scheduled_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_source: Mapped[str] = mapped_column(
        String(30),
        default=JobTriggerSource.API.value,
        nullable=False,
    )
    job_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40),
        default=JobStatus.CREATED.value,
        nullable=False,
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    succeeded_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_batches: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    finished_batches: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Never exposed by Pydantic responses; only the worker decrypts this value.
    encrypted_secrets: Mapped[str | None] = mapped_column(Text, nullable=True)

    creator: Mapped["Auth | None"] = relationship(
        "Auth",
        foreign_keys=lambda: [Job.created_by],
        lazy="joined",
    )
    batches: Mapped[list["JobBatch"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    scheduled_job: Mapped["ScheduledJob | None"] = relationship(
        back_populates="runs",
        foreign_keys=lambda: [Job.scheduled_job_id],
    )

    @property
    def creator_email(self) -> str | None:
        return self.creator.email if self.creator else None

    @property
    def progress_percentage(self) -> float:
        if self.total_items == 0:
            return 0.0
        return round((self.processed_items / self.total_items) * 100, 2)


class JobBatch(Base):
    """Small retryable unit consumed by exactly one worker at a time."""

    __tablename__ = "job_batches"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_enum_values(JobBatchStatus)})",
            name="ck_job_batches_status",
        ),
        UniqueConstraint(
            "job_id",
            "sequence",
            name="uq_job_batches_job_sequence",
        ),
        Index("ix_job_batches_celery_task_id", "celery_task_id"),
        Index("ix_job_batches_job_status", "job_id", "status"),
        {"schema": "jobs"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40),
        default=JobBatchStatus.PENDING.value,
        nullable=False,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    succeeded_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="batches")
    items: Mapped[list["JobItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class JobItem(Base):
    """Result and retry state for one business item, such as a SAP document."""

    __tablename__ = "job_items"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_enum_values(JobItemStatus)})",
            name="ck_job_items_status",
        ),
        UniqueConstraint(
            "job_id",
            "reference",
            name="uq_job_items_job_reference",
        ),
        Index("ix_job_items_job_status", "job_id", "status"),
        Index("ix_job_items_batch_status", "batch_id", "status"),
        {"schema": "jobs"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.job_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default=JobItemStatus.PENDING.value,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    external_status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    result_data: Mapped[dict | list | str | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    safe_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    batch: Mapped[JobBatch] = relationship(back_populates="items")


class ScheduledJob(Base, AuditMixin):
    """Definicion de calendario; cada ejecucion real vive en jobs.jobs."""

    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        CheckConstraint(
            f"schedule_kind IN ({_enum_values(ScheduledJobScheduleKind)})",
            name="ck_scheduled_jobs_schedule_kind",
        ),
        UniqueConstraint("name", name="uq_scheduled_jobs_name"),
        Index("ix_scheduled_jobs_enabled_next_run", "enabled", "next_run_at"),
        Index("ix_scheduled_jobs_job_type", "job_type"),
        {"schema": "jobs"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    job_type: Mapped[str] = mapped_column(String(60), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    schedule_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    batch_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(60),
        default="America/Lima",
        nullable=False,
    )
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_job: Mapped[Job | None] = relationship(
        foreign_keys=[last_job_id],
        post_update=True,
    )
    runs: Mapped[list[Job]] = relationship(
        back_populates="scheduled_job",
        foreign_keys=lambda: [Job.scheduled_job_id],
    )
