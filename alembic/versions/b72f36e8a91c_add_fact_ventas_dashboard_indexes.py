"""add dashboard analytics indexes

Revision ID: b72f36e8a91c
Revises: 7da7715270af
Create Date: 2026-06-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b72f36e8a91c"
down_revision: Union[str, Sequence[str], None] = "7da7715270af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_dim_producto_rubro",
        "dim_producto",
        ["rubro"],
        unique=False,
        schema="coolbox",
    )
    op.create_index(
        "ix_dim_producto_familia",
        "dim_producto",
        ["familia"],
        unique=False,
        schema="coolbox",
    )
    op.create_index(
        "ix_fact_ventas_tienda_fecha",
        "fact_ventas",
        ["tienda_id", "fecha"],
        unique=False,
        schema="coolbox",
    )
    op.create_index(
        "ix_fact_ventas_canal_fecha",
        "fact_ventas",
        ["canal_id", "fecha"],
        unique=False,
        schema="coolbox",
    )
    op.create_index(
        "ix_fact_ventas_fecha_producto",
        "fact_ventas",
        ["fecha", "producto_id"],
        unique=False,
        schema="coolbox",
    )
    op.create_index(
        "ix_fact_ventas_fecha_cliente",
        "fact_ventas",
        ["fecha", "cliente_id"],
        unique=False,
        schema="coolbox",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_fact_ventas_fecha_cliente",
        table_name="fact_ventas",
        schema="coolbox",
    )
    op.drop_index(
        "ix_fact_ventas_fecha_producto",
        table_name="fact_ventas",
        schema="coolbox",
    )
    op.drop_index(
        "ix_fact_ventas_canal_fecha",
        table_name="fact_ventas",
        schema="coolbox",
    )
    op.drop_index(
        "ix_dim_producto_familia",
        table_name="dim_producto",
        schema="coolbox",
    )
    op.drop_index(
        "ix_dim_producto_rubro",
        table_name="dim_producto",
        schema="coolbox",
    )
    op.drop_index(
        "ix_fact_ventas_tienda_fecha",
        table_name="fact_ventas",
        schema="coolbox",
    )
