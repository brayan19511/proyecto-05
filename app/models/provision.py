
from uuid import UUID
from decimal import Decimal
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    func,
    UniqueConstraint,
    Numeric,
)
from app.core.db_postgres import Base

from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID


class AuditMixin:
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=True
    )

    updated_by: Mapped[UUID] = mapped_column(
        ForeignKey("security.auth.id"),
        nullable=True
    )

class Currency(Base, AuditMixin):
    __tablename__ = "currencies"
    __table_args__ = {"schema": "finance"}

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(10))

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
class ProvisionConcept(Base,AuditMixin): 
    __tablename__ = "provision_concepts" 
    __table_args__ = {"schema": "finance"} 
    id: Mapped[int] = mapped_column(primary_key=True) 
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) 
    name: Mapped[str] = mapped_column(String(100), nullable=False) 
    description: Mapped[str] = mapped_column(String(255), nullable=False) 
    active: Mapped[bool] = mapped_column(Boolean, default=True) 
    # Código relacionado en SAP 
    code_sap: Mapped[str] = mapped_column(String(50), nullable=True) 

class Area(Base,AuditMixin): 
    __tablename__ = "areas" 
    __table_args__ = {"schema": "finance"} 
    id: Mapped[int] = mapped_column(primary_key=True) 
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) 
    name: Mapped[str] = mapped_column(String(100), nullable=False) 
    description: Mapped[str] = mapped_column(String(255), nullable=False) 
    active: Mapped[bool] = mapped_column(Boolean, default=True) 

class ProvisionStatus(Base,AuditMixin):
    __tablename__ = "provision_statuses"
    __table_args__ = {"schema": "finance"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))

class Provision(Base, AuditMixin):
    __tablename__ = "provisions"
    __table_args__ = {"schema": "finance"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    ticket_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    status_id: Mapped[int] = mapped_column(
        ForeignKey("finance.provision_statuses.id")
    )

    concept_id: Mapped[int] = mapped_column(
        ForeignKey("finance.provision_concepts.id")
    )

    area_id: Mapped[int] = mapped_column(
        ForeignKey("finance.areas.id")
    )

    currency_id: Mapped[int] = mapped_column(
        ForeignKey("finance.currencies.id")
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    provision_date: Mapped[DateTime] = mapped_column(nullable=True)

    observations: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )

    sap_document_number: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    sap_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Relaciones
    documents = relationship(
        "ProvisionDocument",
        back_populates="provision",
        cascade="all, delete-orphan"
    )

class ProvisionDocument(Base, AuditMixin):
    __tablename__ = "provision_documents"
    __table_args__ = {"schema": "finance"}

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )

    provision_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance.provisions.id")
    )

    document_number: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    supplier_ruc: Mapped[str] = mapped_column(
        String(20),
        nullable=True
    )

    supplier_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    supplier_code: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    document_date: Mapped[DateTime] = mapped_column(
        nullable=True
    )

    provision = relationship(
        "Provision",
        back_populates="documents"
    )

class Attachment(Base, AuditMixin):
    __tablename__ = "attachments"
    __table_args__ = {"schema": "finance"}

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