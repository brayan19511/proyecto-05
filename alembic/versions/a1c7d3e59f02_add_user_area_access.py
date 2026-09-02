"""add user area access (alcance empresa/area por usuario)

Revision ID: a1c7d3e59f02
Revises: c3f1a2b4d5e6
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1c7d3e59f02"
down_revision: Union[str, Sequence[str], None] = "c3f1a2b4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_area_access",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        # NULL = todas las areas de la empresa.
        sa.Column("area_id", sa.Integer(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["area_id"], ["master.areas.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["master.companies.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["security.auth.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["security.auth.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="security",
    )

    # Indices unicos parciales: en Postgres los NULL no colisionan en un
    # UNIQUE normal, asi que se separa el caso "area concreta" del caso
    # "toda la empresa".
    op.create_index(
        "uq_user_area_access_area",
        "user_area_access",
        ["user_id", "company_id", "area_id"],
        unique=True,
        schema="security",
        postgresql_where=sa.text("area_id IS NOT NULL"),
    )
    op.create_index(
        "uq_user_area_access_company",
        "user_area_access",
        ["user_id", "company_id"],
        unique=True,
        schema="security",
        postgresql_where=sa.text("area_id IS NULL"),
    )
    op.create_index(
        "ix_user_area_access_user",
        "user_area_access",
        ["user_id"],
        unique=False,
        schema="security",
    )
    op.create_index(
        "ix_user_area_access_company_area",
        "user_area_access",
        ["company_id", "area_id"],
        unique=False,
        schema="security",
    )

    # La descripcion del area pasa a ser opcional.
    op.alter_column(
        "areas",
        "description",
        existing_type=sa.String(length=255),
        nullable=True,
        schema="master",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE master.areas SET description = '' WHERE description IS NULL"
    )
    op.alter_column(
        "areas",
        "description",
        existing_type=sa.String(length=255),
        nullable=False,
        schema="master",
    )

    op.drop_index(
        "ix_user_area_access_company_area",
        table_name="user_area_access",
        schema="security",
    )
    op.drop_index(
        "ix_user_area_access_user",
        table_name="user_area_access",
        schema="security",
    )
    op.drop_index(
        "uq_user_area_access_company",
        table_name="user_area_access",
        schema="security",
    )
    op.drop_index(
        "uq_user_area_access_area",
        table_name="user_area_access",
        schema="security",
    )
    op.drop_table("user_area_access", schema="security")
