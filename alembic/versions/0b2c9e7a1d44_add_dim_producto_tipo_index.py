"""add dim_producto tipo index

Revision ID: 0b2c9e7a1d44
Revises: d91a0d67c8fe
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0b2c9e7a1d44"
down_revision: Union[str, Sequence[str], None] = "d91a0d67c8fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_dim_producto_tipo",
        "dim_producto",
        ["tipo"],
        unique=False,
        schema="coolbox",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dim_producto_tipo",
        table_name="dim_producto",
        schema="coolbox",
    )
