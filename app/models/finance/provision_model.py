# app/models/finance/provision_model.py

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID
from decimal import Decimal
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
)
from app.core.db_postgres import Base

from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

from app.models.common.mixin_model import AuditMixin

    
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
    company_id: Mapped[int] = mapped_column(
        ForeignKey("master.companies.id"),
        nullable=False
        )

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
        ForeignKey("master.areas.id")
    )

    currency_id: Mapped[int] = mapped_column(
        ForeignKey("master.currencies.id")
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    provision_date: Mapped[datetime] = mapped_column(
    DateTime,
    nullable=True
)

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

    supplier_rut: Mapped[str] = mapped_column(
        String(20),
        nullable=True
    )

    supplier_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    provision = relationship(
        "Provision",
        back_populates="documents"
    )

