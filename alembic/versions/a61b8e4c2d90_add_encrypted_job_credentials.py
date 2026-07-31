"""add encrypted job credentials

Revision ID: a61b8e4c2d90
Revises: f2a7c901d4e8
Create Date: 2026-07-06 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a61b8e4c2d90"
down_revision: str | None = "f2a7c901d4e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("encrypted_secrets", sa.Text(), nullable=True),
        schema="jobs",
    )


def downgrade() -> None:
    op.drop_column("jobs", "encrypted_secrets", schema="jobs")
