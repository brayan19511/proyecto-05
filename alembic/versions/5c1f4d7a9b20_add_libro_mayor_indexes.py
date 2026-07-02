"""add libro mayor indexes

Revision ID: 5c1f4d7a9b20
Revises: 4f76fb53d5bf
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5c1f4d7a9b20"
down_revision: Union[str, Sequence[str], None] = "4f76fb53d5bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_libro_mayor_tipo_fecha",
        "libro_mayor",
        ["tipo_cuenta", "fecha_contabilizacion"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "ix_libro_mayor_tipo_actualizacion",
        "libro_mayor",
        ["tipo_cuenta", "fecha_actualizacion"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "ix_libro_mayor_id_regla",
        "libro_mayor",
        ["id_regla"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "ix_libro_mayor_rule_candidates",
        "libro_mayor",
        ["cuenta_asociada", "cuenta_contrapartida", "centro_costo"],
        unique=False,
        schema="finance",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_libro_mayor_rule_candidates",
        table_name="libro_mayor",
        schema="finance",
    )
    op.drop_index(
        "ix_libro_mayor_id_regla",
        table_name="libro_mayor",
        schema="finance",
    )
    op.drop_index(
        "ix_libro_mayor_tipo_actualizacion",
        table_name="libro_mayor",
        schema="finance",
    )
    op.drop_index(
        "ix_libro_mayor_tipo_fecha",
        table_name="libro_mayor",
        schema="finance",
    )
