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
    
class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = {"schema": "coolbox"}
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    codigo_comercial: Mapped[str] = mapped_column(String, nullable=True)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    marca: Mapped[str] = mapped_column(String, nullable=True)
    rubro: Mapped[str] = mapped_column(String, nullable=True)
    familia: Mapped[str] = mapped_column(String, nullable=True)
    subfamilia: Mapped[str] = mapped_column(String, nullable=True)
    tipo: Mapped[str] = mapped_column(String, nullable=True)
    descatalogado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)