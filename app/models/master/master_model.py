from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class Company(Base, AuditMixin):
    __tablename__ = "companies"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rut: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Currency(Base, AuditMixin):
    __tablename__ = "currencies"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange_rate_to_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        default=Decimal("1"),
        server_default=text("1"),
        nullable=False,
    )
    is_base_currency: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Area(Base, AuditMixin):
    """Catalogo global de areas.

    El amarre con la empresa no vive aqui sino en
    ``security.user_area_access`` (alcance por usuario) y en el
    ``company_id`` de cada documento, para no duplicar el catalogo por
    sociedad.
    """

    __tablename__ = "areas"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Module(Base, AuditMixin):
    """Interruptor de encendido/apagado por modulo funcional del sistema.

    Una fila por modulo (``sap``, ``email``, ``ledger``...). Es el nivel
    "de negocio": el operador lo apaga en caliente desde el panel y no
    requiere despliegue. El nivel "de infraestructura" vive en la variable
    MODULES_DISABLED del .env y manda sobre esta tabla.
    """

    __tablename__ = "modules"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    # Motivo que el operador dejo al apagarlo; se muestra en el 503 para que
    # quien reporte el problema sepa por que esta apagado y no abra un ticket.
    disabled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
