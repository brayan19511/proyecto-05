# app/models/coolbox/ventas/coolbox_ventas_model.py
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.db_postgres import Base


class Ventas(Base):
    __tablename__ = "ventas"
    __table_args__ = {"schema": "coolbox"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    documento: Mapped[str] = mapped_column(String, nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String, nullable=False)
    tienda: Mapped[str] = mapped_column(String, nullable=False)
    producto: Mapped[str] = mapped_column(String, nullable=False)
    cantidad: Mapped[int] = mapped_column(nullable=False)
    precio: Mapped[float] = mapped_column(nullable=False)
    descuento: Mapped[float] = mapped_column(nullable=False)
    total: Mapped[float] = mapped_column(nullable=False)
    canal: Mapped[str] = mapped_column(String, nullable=False)
    cliente: Mapped[str] = mapped_column(String, nullable=True)
    vendedor: Mapped[str] = mapped_column(String, nullable=True)
    iva: Mapped[float] = mapped_column(nullable=True)


    # new modelo
    # app/models/coolbox/ventas/coolbox_ventas_model.py


from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.db_postgres import Base


class StgVenta(Base):
    __tablename__ = "stg_ventas"
    __table_args__ = (
        Index("ix_stg_ventas_fecha", "fecha"),
        Index("ix_stg_ventas_documento", "documento"),
        {"schema": "coolbox"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    documento: Mapped[str] = mapped_column(String, nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String, nullable=False)

    tienda_codigo: Mapped[str] = mapped_column(String, nullable=False)
    producto_codigo: Mapped[str] = mapped_column(String, nullable=False)
    canal_codigo: Mapped[str] = mapped_column(String, nullable=False)

    cliente_codigo: Mapped[str | None] = mapped_column(String, nullable=True)
    vendedor_codigo: Mapped[str | None] = mapped_column(String, nullable=True)

    cantidad: Mapped[int] = mapped_column(nullable=False)
    precio: Mapped[float] = mapped_column(nullable=False)
    descuento: Mapped[float] = mapped_column(nullable=False)
    total: Mapped[float] = mapped_column(nullable=False)
    iva: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


class DimProducto(Base):
    __tablename__ = "dim_producto"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_dim_producto_codigo"),
        Index("ix_dim_producto_codigo", "codigo"),
        Index("ix_dim_producto_rubro", "rubro"),
        Index("ix_dim_producto_familia", "familia"),
        Index("ix_dim_producto_tipo", "tipo"),
        {"schema": "coolbox"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    codigo: Mapped[str] = mapped_column(String, nullable=False)
    codigo_comercial: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)

    marca: Mapped[str | None] = mapped_column(String, nullable=True)
    rubro: Mapped[str | None] = mapped_column(String, nullable=True)
    familia: Mapped[str | None] = mapped_column(String, nullable=True)
    subfamilia: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String, nullable=True)

    descatalogado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=func.now(),
    )

    ventas: Mapped[list["FactVenta"]] = relationship(back_populates="producto")


class DimTienda(Base):
    __tablename__ = "dim_tienda"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_dim_tienda_codigo"),
        Index("ix_dim_tienda_codigo", "codigo"),
        {"schema": "coolbox"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    codigo: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)

    categoria: Mapped[str | None] = mapped_column(String, nullable=True)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    formato: Mapped[str | None] = mapped_column(String, nullable=True)

    latitud: Mapped[float | None] = mapped_column(nullable=True)
    longitud: Mapped[float | None] = mapped_column(nullable=True)
    metraje: Mapped[float | None] = mapped_column(nullable=True)

    ubigeo: Mapped[str | None] = mapped_column(String, nullable=True)
    departamento: Mapped[str | None] = mapped_column(String, nullable=True)
    provincia: Mapped[str | None] = mapped_column(String, nullable=True)
    distrito: Mapped[str | None] = mapped_column(String, nullable=True)

    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=func.now(),
    )

    ventas: Mapped[list["FactVenta"]] = relationship(back_populates="tienda")


class DimCanal(Base):
    __tablename__ = "dim_canal"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_dim_canal_codigo"),
        Index("ix_dim_canal_codigo", "codigo"),
        {"schema": "coolbox"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    codigo: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=func.now(),
    )

    ventas: Mapped[list["FactVenta"]] = relationship(back_populates="canal")


class DimCliente(Base):
    __tablename__ = "dim_cliente"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_dim_cliente_codigo"),
        Index("ix_dim_cliente_codigo", "codigo"),
        {"schema": "coolbox"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Solo código interno, sin datos sensibles
    codigo: Mapped[str] = mapped_column(String, nullable=False)

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=func.now(),
    )

    ventas: Mapped[list["FactVenta"]] = relationship(back_populates="cliente")


class FactVenta(Base):
    __tablename__ = "fact_ventas"
    __table_args__ = (
        UniqueConstraint(
            "fecha",
            "documento",
            "producto_id",
            "precio",
            name="uq_fact_venta_linea",
        ),
        Index("ix_fact_ventas_fecha", "fecha"),
        Index("ix_fact_ventas_documento", "documento"),
        Index("ix_fact_ventas_producto_id", "producto_id"),
        Index("ix_fact_ventas_tienda_id", "tienda_id"),
        Index("ix_fact_ventas_canal_id", "canal_id"),
        Index("ix_fact_ventas_cliente_id", "cliente_id"),
        Index("ix_fact_ventas_tienda_fecha", "tienda_id", "fecha"),
        Index("ix_fact_ventas_canal_fecha", "canal_id", "fecha"),
        Index("ix_fact_ventas_fecha_producto", "fecha", "producto_id"),
        Index("ix_fact_ventas_fecha_cliente", "fecha", "cliente_id"),
        {"schema": "coolbox"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    documento: Mapped[str] = mapped_column(String, nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String, nullable=False)

    producto_id: Mapped[UUID] = mapped_column(
        ForeignKey("coolbox.dim_producto.id"),
        nullable=False,
    )

    tienda_id: Mapped[UUID] = mapped_column(
        ForeignKey("coolbox.dim_tienda.id"),
        nullable=False,
    )

    canal_id: Mapped[UUID] = mapped_column(
        ForeignKey("coolbox.dim_canal.id"),
        nullable=False,
    )

    cliente_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("coolbox.dim_cliente.id"),
        nullable=True,
    )

    cantidad: Mapped[int] = mapped_column(nullable=False)
    precio: Mapped[float] = mapped_column(nullable=False)
    descuento: Mapped[float] = mapped_column(nullable=False)
    total: Mapped[float] = mapped_column(nullable=False)
    iva: Mapped[float | None] = mapped_column(nullable=True)

    vendedor_codigo: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    producto: Mapped["DimProducto"] = relationship(back_populates="ventas")

    tienda: Mapped["DimTienda"] = relationship(back_populates="ventas")

    canal: Mapped["DimCanal"] = relationship(back_populates="ventas")

    cliente: Mapped["DimCliente"] = relationship(back_populates="ventas")
