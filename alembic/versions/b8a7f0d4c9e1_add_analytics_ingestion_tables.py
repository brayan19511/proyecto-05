"""add analytics ingestion tables

Revision ID: b8a7f0d4c9e1
Revises: 7b9d2e41c6a3
Create Date: 2026-08-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b8a7f0d4c9e1"
down_revision: Union[str, None] = "7b9d2e41c6a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "analytics"')
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("source_code", sa.String(length=40), nullable=False),
        sa.Column("table_name", sa.String(length=120), nullable=False),
        sa.Column("table_kind", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["security.auth.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="analytics",
    )
    op.create_index(
        "ix_ingestion_runs_source_table_created",
        "ingestion_runs",
        ["source_code", "table_name", "created_at"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "ix_ingestion_runs_status_created",
        "ingestion_runs",
        ["status", "created_at"],
        unique=False,
        schema="analytics",
    )
    op.create_table(
        "ingestion_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=160), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["analytics.ingestion_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="analytics",
    )
    op.create_index(
        "ix_ingestion_items_run_reference",
        "ingestion_items",
        ["run_id", "reference"],
        unique=True,
        schema="analytics",
    )
    op.create_index(
        "ix_ingestion_items_status",
        "ingestion_items",
        ["status"],
        unique=False,
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_items_status", table_name="ingestion_items", schema="analytics")
    op.drop_index("ix_ingestion_items_run_reference", table_name="ingestion_items", schema="analytics")
    op.drop_table("ingestion_items", schema="analytics")
    op.drop_index("ix_ingestion_runs_status_created", table_name="ingestion_runs", schema="analytics")
    op.drop_index("ix_ingestion_runs_source_table_created", table_name="ingestion_runs", schema="analytics")
    op.drop_table("ingestion_runs", schema="analytics")
