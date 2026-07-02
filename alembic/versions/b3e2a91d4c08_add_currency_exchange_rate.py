"""add currency exchange rate

Revision ID: b3e2a91d4c08
Revises: 7b2d8f0c1a34
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3e2a91d4c08"
down_revision: Union[str, Sequence[str], None] = "7b2d8f0c1a34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "currencies",
        sa.Column(
            "exchange_rate_to_base",
            sa.Numeric(18, 6),
            nullable=False,
            server_default="1",
        ),
        schema="master",
    )
    op.add_column(
        "currencies",
        sa.Column(
            "is_base_currency",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="master",
    )

    op.execute(
        """
        UPDATE master.currencies
        SET exchange_rate_to_base = 1,
            is_base_currency = true
        WHERE code = 'PEN'
        """
    )
    op.execute(
        """
        UPDATE master.currencies
        SET exchange_rate_to_base = 3.75
        WHERE code = 'USD'
        """
    )
    op.execute(
        """
        UPDATE master.currencies
        SET exchange_rate_to_base = 4.05
        WHERE code = 'EUR'
        """
    )


def downgrade() -> None:
    op.drop_column("currencies", "is_base_currency", schema="master")
    op.drop_column("currencies", "exchange_rate_to_base", schema="master")
