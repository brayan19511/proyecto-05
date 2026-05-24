# app/models/master/master_model.py

from sqlalchemy import (
    String,
    Boolean,
    Text,
)
from app.core.db_postgres import Base

from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

from app.models.common.mixin_model import AuditMixin


class Company(Base, AuditMixin):
    __tablename__ = "companies"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    rut: Mapped[str] = mapped_column(
        String(20),
        nullable=True
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    
    
    
class Currency(Base, AuditMixin):
    __tablename__ = "currencies"
    __table_args__ = {"schema": "master"}

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(10))

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
class Area(Base,AuditMixin): 
    __tablename__ = "areas" 
    __table_args__ = {"schema": "master"} 
    id: Mapped[int] = mapped_column(primary_key=True) 
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) 
    name: Mapped[str] = mapped_column(String(100), nullable=False) 
    description: Mapped[str] = mapped_column(String(255), nullable=False) 
    active: Mapped[bool] = mapped_column(Boolean, default=True) 
class Attachment(Base, AuditMixin):
    __tablename__ = "attachments"
    __table_args__ = {"schema": "storage"}

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )
    # definir el tipo de entidad a la que se adjunta el archivo (provision, provision_document, etc.)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    # definir el ID de la entidad a la que se adjunta el archivo (por ejemplo, el ID de la provisión o del documento)
    entity_id: Mapped[UUID] = mapped_column(
        nullable=False
    )

    file_name: Mapped[str] = mapped_column(
        String(255)
    )

    file_extension: Mapped[str] = mapped_column(
        String(20)
    )

    mime_type: Mapped[str] = mapped_column(
        String(100)
    )
    storage_type: Mapped[str] = mapped_column(
        String(20),nullable=True
    )
    file_size: Mapped[int] = mapped_column(nullable=True)

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )

    file_base64: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )