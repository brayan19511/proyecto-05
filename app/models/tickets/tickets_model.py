
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text

from app.core.db.db_postgres import Base
from app.models.common.mixin_model import AuditMixin

from sqlalchemy.orm import Mapped, mapped_column

class Tickets(Base, AuditMixin):
    __tablename__ = "tickets"
    numero_de_ticket: Mapped[int] = mapped_column(primary_key=True)
    fecha_de_creacion: Mapped[DateTime] = mapped_column(DateTime)
    creado_por: Mapped[Optional[str]] = mapped_column(String)
    area: Mapped[Optional[str]] = mapped_column(String)
    sub_area_tienda: Mapped[Optional[str]] = mapped_column(String)
    categoria: Mapped[Optional[str]] = mapped_column(String)
    nombres_del_solicitante: Mapped[Optional[str]] = mapped_column(String)
    numero_telefonico: Mapped[Optional[int]] = mapped_column(Integer)
    medio_de_contacto: Mapped[Optional[str]] = mapped_column(String)
    area_del_servicio: Mapped[Optional[str]] = mapped_column(String)
    asunto: Mapped[Optional[str]] = mapped_column(String)
    detalles: Mapped[Optional[str]] = mapped_column(Text)
    causa_raiz: Mapped[Optional[str]] = mapped_column(String)
    nivel: Mapped[Optional[int]] = mapped_column(Integer)
    fecha_nivel_1: Mapped[DateTime] = mapped_column(DateTime)
    resolucion_nivel_1: Mapped[Optional[str]] = mapped_column(String)
    soporte_nivel_1: Mapped[Optional[str]] = mapped_column(String)
    fecha_nivel_2: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    resolucion_nivel_2: Mapped[Optional[str]] = mapped_column(String)
    soporte_nivel_2: Mapped[Optional[str]] = mapped_column(String)
    asignado_a: Mapped[Optional[str]] = mapped_column(String)
    estado: Mapped[Optional[str]] = mapped_column(String)
    
