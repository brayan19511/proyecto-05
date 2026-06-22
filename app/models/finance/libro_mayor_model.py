from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlalchemy import (
    BIGINT,
    INT,
    String,
    Boolean,
    DateTime,
    Date,
    Numeric,
    UniqueConstraint,
    Index,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin


class ReglasGastos(Base, AuditMixin):
    __tablename__ = "reglas_gastos"
    __table_args__ = {"schema": "finance"}
    id_regla: Mapped[int] = mapped_column(primary_key=True)
    prioridad: Mapped[int] = mapped_column(INT, nullable=False)
    tipo_regla: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'CUENTA', 'MIXTA', 'TEXTO'
    cuenta: Mapped[str] = mapped_column(
        String(15), nullable=True
    )  # Mapea con cuenta_asociada de SAP
    cuenta_contrapartida: Mapped[str] = mapped_column(String(15), nullable=True)
    centro_costo: Mapped[str] = mapped_column(String(30), nullable=True)
    filtro_texto: Mapped[str] = mapped_column(
        String(255), nullable=True
    )  # Texto que debe incluir
    texto_excluido: Mapped[str] = mapped_column(
        String(255), nullable=True
    )  # Texto que NO debe incluir
    monto_min: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=True)
    monto_max: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=True)
    codigo: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Categoría Ejecutiva 1
    subcodigo: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Categoría Ejecutiva 2
    nombre_cuenta: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Nombre Destino para Reporte
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LibroMayor(Base, AuditMixin):
    __tablename__ = "libro_mayor"
    __table_args__ = (
        UniqueConstraint("transaccion_id", "linea"),
        Index(
            "ix_libro_mayor_tipo_fecha",
            "tipo_cuenta",
            "fecha_contabilizacion",
        ),
        Index(
            "ix_libro_mayor_tipo_actualizacion",
            "tipo_cuenta",
            "fecha_actualizacion",
        ),
        Index(
            "ix_libro_mayor_id_regla",
            "id_regla",
        ),
        Index(
            "ix_libro_mayor_rule_candidates",
            "cuenta_asociada",
            "cuenta_contrapartida",
            "centro_costo",
        ),
        {"schema": "finance"},
    )
    transaccion_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    linea: Mapped[int] = mapped_column(INT, primary_key=True)
    fecha_contabilizacion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_documento: Mapped[date] = mapped_column(Date, nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(50), nullable=False)
    transaccion_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    folio: Mapped[str] = mapped_column(String(50), nullable=True)
    tipo_documento: Mapped[str] = mapped_column(String(50), nullable=True)
    tipo_cuenta: Mapped[str] = mapped_column(String(50), nullable=True)
    cuenta_asociada: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre_cuenta_asociada: Mapped[str] = mapped_column(String(100), nullable=False)
    proveedor: Mapped[str] = mapped_column(String(255), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=True)
    comentario_linea: Mapped[str] = mapped_column(String(255), nullable=True)
    cuenta_contrapartida: Mapped[str] = mapped_column(String(100), nullable=True)
    nombre_contrapartida: Mapped[str] = mapped_column(String(150), nullable=True)
    referencia_1: Mapped[str] = mapped_column(String(200), nullable=True)
    referencia_2: Mapped[str] = mapped_column(String(200), nullable=True)
    referencia_3: Mapped[str] = mapped_column(String(200), nullable=True)
    cargo_abono_ml: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    cargo_abono_me: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    centro_costo: Mapped[str] = mapped_column(String(100), nullable=True)
    centro_area: Mapped[str] = mapped_column(String(100), nullable=True)
    nombre_area: Mapped[str] = mapped_column(String(100), nullable=True)

    id_regla: Mapped[int] = mapped_column(INT, nullable=True)
    tiene_regla: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    subcodigo: Mapped[str] = mapped_column(String(50), nullable=True)
    nombre_cuenta: Mapped[str] = mapped_column(String(100), nullable=False)

    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
