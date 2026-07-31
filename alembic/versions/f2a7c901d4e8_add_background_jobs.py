"""add background jobs

Revision ID: f2a7c901d4e8
Revises: c4d7e18a52bf
Create Date: 2026-07-06 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2a7c901d4e8"
down_revision: str | None = "c4d7e18a52bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "jobs"')

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_job_id", sa.Uuid(), nullable=True),
        sa.Column("job_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("succeeded_items", sa.Integer(), nullable=False),
        sa.Column("failed_items", sa.Integer(), nullable=False),
        sa.Column("cancelled_items", sa.Integer(), nullable=False),
        sa.Column("total_batches", sa.Integer(), nullable=False),
        sa.Column("finished_batches", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "status IN ('CREATED', 'QUEUED', 'DISPATCH_FAILED', 'RUNNING', "
            "'CANCEL_REQUESTED', 'CANCELLED', 'COMPLETED', "
            "'COMPLETED_WITH_ERRORS', 'FAILED')",
            name="ck_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["security.auth.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_job_id"],
            ["jobs.jobs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["security.auth.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "created_by",
            "job_type",
            "idempotency_key",
            name="uq_jobs_creator_type_idempotency",
        ),
        schema="jobs",
    )
    op.create_index(
        "ix_jobs_created_by_created_at",
        "jobs",
        ["created_by", "created_at"],
        schema="jobs",
    )
    op.create_index(
        "ix_jobs_job_type",
        "jobs",
        ["job_type"],
        schema="jobs",
    )
    op.create_index(
        "ix_jobs_parent_job_id",
        "jobs",
        ["parent_job_id"],
        schema="jobs",
    )
    op.create_index(
        "ix_jobs_status_created_at",
        "jobs",
        ["status", "created_at"],
        schema="jobs",
    )

    op.create_table(
        "job_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("celery_task_id", sa.String(length=100), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("succeeded_items", sa.Integer(), nullable=False),
        sa.Column("failed_items", sa.Integer(), nullable=False),
        sa.Column("cancelled_items", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'QUEUED', 'RUNNING', 'RETRYING', "
            "'COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED', 'CANCELLED')",
            name="ck_job_batches_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "sequence",
            name="uq_job_batches_job_sequence",
        ),
        schema="jobs",
    )
    op.create_index(
        "ix_job_batches_celery_task_id",
        "job_batches",
        ["celery_task_id"],
        schema="jobs",
    )
    op.create_index(
        "ix_job_batches_job_status",
        "job_batches",
        ["job_id", "status"],
        schema="jobs",
    )

    op.create_table(
        "job_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("external_status_code", sa.Integer(), nullable=True),
        sa.Column(
            "result_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', "
            "'CANCELLED')",
            name="ck_job_items_status",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["jobs.job_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "reference",
            name="uq_job_items_job_reference",
        ),
        schema="jobs",
    )
    op.create_index(
        "ix_job_items_batch_status",
        "job_items",
        ["batch_id", "status"],
        schema="jobs",
    )
    op.create_index(
        "ix_job_items_job_status",
        "job_items",
        ["job_id", "status"],
        schema="jobs",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_items_job_status",
        table_name="job_items",
        schema="jobs",
    )
    op.drop_index(
        "ix_job_items_batch_status",
        table_name="job_items",
        schema="jobs",
    )
    op.drop_table("job_items", schema="jobs")

    op.drop_index(
        "ix_job_batches_job_status",
        table_name="job_batches",
        schema="jobs",
    )
    op.drop_index(
        "ix_job_batches_celery_task_id",
        table_name="job_batches",
        schema="jobs",
    )
    op.drop_table("job_batches", schema="jobs")

    op.drop_index(
        "ix_jobs_status_created_at",
        table_name="jobs",
        schema="jobs",
    )
    op.drop_index(
        "ix_jobs_parent_job_id",
        table_name="jobs",
        schema="jobs",
    )
    op.drop_index(
        "ix_jobs_job_type",
        table_name="jobs",
        schema="jobs",
    )
    op.drop_index(
        "ix_jobs_created_by_created_at",
        table_name="jobs",
        schema="jobs",
    )
    op.drop_table("jobs", schema="jobs")
