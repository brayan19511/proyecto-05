"""add master.modules (interruptor de modulos)

Revision ID: d4b1e6f28a35
Revises: a1c7d3e59f02
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4b1e6f28a35"
down_revision: Union[str, Sequence[str], None] = "a1c7d3e59f02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Catalogo inicial. Se inserta aqui y no solo en el seed para que un despliegue
# que corre migraciones sin seed igual tenga el panel poblado.
MODULES = [
    ("sap", "Integracion SAP", "Envio de documentos y conciliacion contra SAP"),
    ("email", "Envio de correos", "Salida SMTP de todo el sistema"),
    (
        "payment_provider",
        "Pagos a proveedores",
        "Constancias de pago y su envio por correo",
    ),
    ("ledger", "Libro mayor", "Sincronizacion y consulta del libro mayor"),
    ("provisions", "Provisiones", "Registro y aprobacion de provisiones"),
    (
        "sales_channel",
        "Canales de venta (Last Miller)",
        "SKUs y promociones de Rappi y PedidosYa",
    ),
    ("attendance", "Asistencia", "Consulta de marcas de asistencia"),
    ("analytics", "Analitica", "Ingesta ICG al data lake y capa silver"),
    ("icg_query", "Consultas ICG (GraphQL)", "Lectura directa de ICG por GraphQL"),
]


def upgrade() -> None:
    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("disabled_reason", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["security.auth.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_modules_code"),
        schema="master",
    )

    modules_table = sa.table(
        "modules",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        schema="master",
    )

    op.bulk_insert(
        modules_table,
        [
            {"code": code, "name": name, "description": description}
            for code, name, description in MODULES
        ],
    )


def downgrade() -> None:
    op.drop_table("modules", schema="master")
