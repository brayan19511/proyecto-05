"""add payment provider and mail template tables

Revision ID: d0f4a8c9b7e2
Revises: a61b8e4c2d90
Create Date: 2026-07-13 20:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d0f4a8c9b7e2"
down_revision: str | None = "a61b8e4c2d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def audit_columns():
    return [
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["security.auth.id"]),
    ]


def upgrade() -> None:
    op.create_table(
        "payment_providers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tax_id", sa.String(length=20), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column(
            "commercial_names",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "normalized_names",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "emails_payments",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        *audit_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tax_id", name="uq_payment_provider_tax_id"),
        schema="finance",
    )
    op.create_index(
        "ix_payment_provider_legal_name",
        "payment_providers",
        ["legal_name"],
        schema="finance",
    )

    op.create_table(
        "mail_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("template", sa.Text(), nullable=True),
        sa.Column("mail_from", sa.String(length=255), nullable=True),
        sa.Column("mail_to", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("cc", sa.Text(), nullable=True),
        sa.Column("bcc", sa.Text(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        *audit_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_mail_template_name"),
        schema="master",
    )


def downgrade() -> None:
    op.drop_table("mail_templates", schema="master")
    op.drop_index(
        "ix_payment_provider_legal_name",
        table_name="payment_providers",
        schema="finance",
    )
    op.drop_table("payment_providers", schema="finance")
