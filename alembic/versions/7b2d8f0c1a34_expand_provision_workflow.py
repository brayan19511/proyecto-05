"""expand provision workflow

Revision ID: 7b2d8f0c1a34
Revises: 5c1f4d7a9b20
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7b2d8f0c1a34"
down_revision: Union[str, Sequence[str], None] = "5c1f4d7a9b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "provisions",
        sa.Column("supplier_tax_id", sa.String(length=20), nullable=True),
        schema="finance",
    )
    op.add_column(
        "provisions",
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        schema="finance",
    )
    op.add_column(
        "provisions",
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        schema="finance",
    )
    op.add_column(
        "provisions",
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        schema="finance",
    )
    op.add_column(
        "provisions",
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="finance",
    )
    op.add_column(
        "provisions",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        schema="finance",
    )
    op.add_column(
        "provisions",
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        schema="finance",
    )
    op.create_foreign_key(
        "fk_provisions_reviewed_by_user_id_auth",
        "provisions",
        "auth",
        ["reviewed_by_user_id"],
        ["id"],
        source_schema="finance",
        referent_schema="security",
    )
    op.create_index(
        "ix_provision_area_status",
        "provisions",
        ["area_id", "status_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "ix_provision_created_by",
        "provisions",
        ["created_by"],
        unique=False,
        schema="finance",
    )

    op.add_column(
        "provision_documents",
        sa.Column("document_date", sa.Date(), nullable=True),
        schema="finance",
    )
    op.add_column(
        "provision_documents",
        sa.Column("description", sa.String(length=255), nullable=True),
        schema="finance",
    )

    op.create_table(
        "provision_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_type", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["provision_id"], ["finance.provisions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["security.auth.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provision_id", "user_id", name="uq_provision_access_user"),
        schema="finance",
    )
    op.create_index(
        "ix_provision_access_user",
        "provision_access",
        ["user_id"],
        unique=False,
        schema="finance",
    )

    op.execute(
        """
        INSERT INTO finance.provision_statuses (code, name)
        VALUES
            ('DRAFT', 'Borrador'),
            ('PENDING_DETAIL', 'Pendiente de completar detalle'),
            ('READY_FOR_REVIEW', 'Listo para revision'),
            ('REVIEWING', 'En revision'),
            ('APPROVED', 'Aprobado'),
            ('REJECTED_FOR_EDIT', 'Observado para corregir'),
            ('REJECTED_FINAL', 'Rechazado definitivo'),
            ('CANCELLED', 'Cancelado'),
            ('POSTED_SAP', 'Registrado en SAP'),
            ('SAP_ERROR', 'Error SAP')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DELETE FROM finance.provision_statuses
        WHERE code IN (
            'DRAFT',
            'PENDING_DETAIL',
            'READY_FOR_REVIEW',
            'REVIEWING',
            'APPROVED',
            'REJECTED_FOR_EDIT',
            'REJECTED_FINAL',
            'CANCELLED',
            'POSTED_SAP',
            'SAP_ERROR'
        )
        """
    )

    op.drop_index(
        "ix_provision_access_user",
        table_name="provision_access",
        schema="finance",
    )
    op.drop_table("provision_access", schema="finance")

    op.drop_column("provision_documents", "description", schema="finance")
    op.drop_column("provision_documents", "document_date", schema="finance")

    op.drop_index(
        "ix_provision_created_by",
        table_name="provisions",
        schema="finance",
    )
    op.drop_index(
        "ix_provision_area_status",
        table_name="provisions",
        schema="finance",
    )
    op.drop_constraint(
        "fk_provisions_reviewed_by_user_id_auth",
        "provisions",
        schema="finance",
        type_="foreignkey",
    )
    op.drop_column("provisions", "closed_at", schema="finance")
    op.drop_column("provisions", "reviewed_at", schema="finance")
    op.drop_column("provisions", "reviewed_by_user_id", schema="finance")
    op.drop_column("provisions", "submitted_at", schema="finance")
    op.drop_column("provisions", "active", schema="finance")
    op.drop_column("provisions", "supplier_name", schema="finance")
    op.drop_column("provisions", "supplier_tax_id", schema="finance")
