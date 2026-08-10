"""add audit logs analytics indexes

Revision ID: c3f1a2b4d5e6
Revises: b8a7f0d4c9e1
Create Date: 2026-08-10 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c3f1a2b4d5e6"
down_revision: Union[str, None] = "b8a7f0d4c9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Indices para las agregaciones de observabilidad (filtros por rango de
    # fecha y por clase de estado). audit.logs solo indexaba trace_id.
    op.create_index(
        "ix_logs_created_at",
        "logs",
        ["created_at"],
        schema="audit",
    )
    op.create_index(
        "ix_logs_status_created_at",
        "logs",
        ["status_code", "created_at"],
        schema="audit",
    )


def downgrade() -> None:
    op.drop_index("ix_logs_status_created_at", table_name="logs", schema="audit")
    op.drop_index("ix_logs_created_at", table_name="logs", schema="audit")
