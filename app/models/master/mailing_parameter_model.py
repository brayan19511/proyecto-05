from sqlalchemy import Boolean, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class MailingParameter(Base, AuditMixin):
    """Parametros reutilizables para enviar correos desde distintos flujos."""

    __tablename__ = "mailing_parameters"
    __table_args__ = (
        UniqueConstraint("name", name="uq_mailing_parameter_name"),
        {"schema": "master"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    mp_from: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cc: Mapped[str | None] = mapped_column(Text, nullable=True)
    bcc: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
