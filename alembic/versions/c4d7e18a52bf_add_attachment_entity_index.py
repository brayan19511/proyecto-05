"""add attachment entity index

Revision ID: c4d7e18a52bf
Revises: b3e2a91d4c08
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c4d7e18a52bf"
down_revision: Union[str, Sequence[str], None] = "b3e2a91d4c08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_attachments_entity_type_entity_id",
        "attachments",
        ["entity_type", "entity_id"],
        unique=False,
        schema="storage",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attachments_entity_type_entity_id",
        table_name="attachments",
        schema="storage",
    )
