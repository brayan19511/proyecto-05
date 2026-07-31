"""rename mail templates to mailing parameters

Revision ID: e2c9a71b0f34
Revises: d0f4a8c9b7e2
Create Date: 2026-07-13 22:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e2c9a71b0f34"
down_revision: str | None = "d0f4a8c9b7e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table(
        "mail_templates",
        "mailing_parameters",
        schema="master",
    )
    op.drop_constraint(
        "uq_mail_template_name",
        "mailing_parameters",
        schema="master",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_mailing_parameter_name",
        "mailing_parameters",
        ["name"],
        schema="master",
    )
    op.add_column(
        "mailing_parameters",
        sa.Column("template_html", sa.Text(), nullable=True),
        schema="master",
    )
    op.add_column(
        "mailing_parameters",
        sa.Column("template_text", sa.Text(), nullable=True),
        schema="master",
    )
    op.alter_column(
        "mailing_parameters",
        "mail_from",
        new_column_name="mp_from",
        schema="master",
    )
    op.alter_column(
        "mailing_parameters",
        "mail_to",
        new_column_name="to",
        schema="master",
    )


def downgrade() -> None:
    op.alter_column(
        "mailing_parameters",
        "to",
        new_column_name="mail_to",
        schema="master",
    )
    op.alter_column(
        "mailing_parameters",
        "mp_from",
        new_column_name="mail_from",
        schema="master",
    )
    op.drop_column("mailing_parameters", "template_text", schema="master")
    op.drop_column("mailing_parameters", "template_html", schema="master")
    op.drop_constraint(
        "uq_mailing_parameter_name",
        "mailing_parameters",
        schema="master",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_mail_template_name",
        "mailing_parameters",
        ["name"],
        schema="master",
    )
    op.rename_table(
        "mailing_parameters",
        "mail_templates",
        schema="master",
    )
