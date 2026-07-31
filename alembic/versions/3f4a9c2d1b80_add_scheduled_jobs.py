"""add scheduled jobs

Revision ID: 3f4a9c2d1b80
Revises: e2c9a71b0f34
Create Date: 2026-07-28 04:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "3f4a9c2d1b80"
down_revision: str | None = "e2c9a71b0f34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("job_type", sa.String(length=60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("schedule_kind", sa.String(length=30), nullable=False),
        sa.Column(
            "schedule_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(length=60), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_id", sa.Uuid(), nullable=True),
        sa.Column("last_status", sa.String(length=40), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
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
            "schedule_kind IN ('DAILY', 'INTERVAL_MINUTES', 'WINDOW_INTERVAL')",
            name="ck_scheduled_jobs_schedule_kind",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(
            ["last_job_id"],
            ["jobs.jobs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["security.auth.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_scheduled_jobs_name"),
        schema="jobs",
    )
    op.create_index(
        "ix_scheduled_jobs_enabled_next_run",
        "scheduled_jobs",
        ["enabled", "next_run_at"],
        schema="jobs",
    )
    op.create_index(
        "ix_scheduled_jobs_job_type",
        "scheduled_jobs",
        ["job_type"],
        schema="jobs",
    )

    op.add_column(
        "jobs",
        sa.Column("scheduled_job_id", sa.Uuid(), nullable=True),
        schema="jobs",
    )
    op.create_foreign_key(
        "fk_jobs_scheduled_job_id",
        "jobs",
        "scheduled_jobs",
        ["scheduled_job_id"],
        ["id"],
        source_schema="jobs",
        referent_schema="jobs",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_jobs_scheduled_job_id",
        "jobs",
        ["scheduled_job_id"],
        schema="jobs",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_jobs_scheduled_job_id",
        table_name="jobs",
        schema="jobs",
    )
    op.drop_constraint(
        "fk_jobs_scheduled_job_id",
        "jobs",
        schema="jobs",
        type_="foreignkey",
    )
    op.drop_column("jobs", "scheduled_job_id", schema="jobs")

    op.drop_index(
        "ix_scheduled_jobs_job_type",
        table_name="scheduled_jobs",
        schema="jobs",
    )
    op.drop_index(
        "ix_scheduled_jobs_enabled_next_run",
        table_name="scheduled_jobs",
        schema="jobs",
    )
    op.drop_table("scheduled_jobs", schema="jobs")
