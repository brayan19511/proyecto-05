"""add job trigger source

Revision ID: 7b9d2e41c6a3
Revises: 3f4a9c2d1b80
Create Date: 2026-07-28 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7b9d2e41c6a3"
down_revision: Union[str, None] = "3f4a9c2d1b80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "trigger_source",
            sa.String(length=30),
            server_default="API",
            nullable=False,
        ),
        schema="jobs",
    )
    op.create_check_constraint(
        "ck_jobs_trigger_source",
        "jobs",
        "trigger_source IN ('API', 'SCHEDULED', 'SCHEDULED_MANUAL', 'RETRY')",
        schema="jobs",
    )
    op.create_index(
        "ix_jobs_trigger_source_created_at",
        "jobs",
        ["trigger_source", "created_at"],
        schema="jobs",
    )
    op.alter_column(
        "jobs",
        "trigger_source",
        server_default=None,
        schema="jobs",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_jobs_trigger_source_created_at",
        table_name="jobs",
        schema="jobs",
    )
    op.drop_constraint(
        "ck_jobs_trigger_source",
        "jobs",
        schema="jobs",
        type_="check",
    )
    op.drop_column("jobs", "trigger_source", schema="jobs")
