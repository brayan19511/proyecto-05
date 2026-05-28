# app/models/finance/provision_model.py
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    Index,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.db_postgres import Base
from app.models.common.mixin_model import AuditMixin
from app.models.master.master_model import Company
if TYPE_CHECKING:
    from app.models.master.master_model import Currency, Area
    from app.models.auth import Auth
# =========================================================
# PROVISION CONCEPT
# =========================================================


class ProvisionConcept(Base, AuditMixin):
    __tablename__ = "provision_concepts"
    __table_args__ = (
        UniqueConstraint("company_id", "code"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(String(50), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    code_sap: Mapped[str | None] = mapped_column(String(50), nullable=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("master.companies.id"), nullable=False, index=True
    )

    # Relaciones
    company: Mapped["Company"] = relationship()
    provisions: Mapped[list["Provision"]] = relationship(back_populates="concept")
    @property
    def company_code(self):
        return self.company.code if self.company else None

# =========================================================
# PROVISION STATUS
# =========================================================


class ProvisionStatus(Base, AuditMixin):
    __tablename__ = "provision_statuses"
    __table_args__ = {"schema": "finance"}

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relaciones
    provisions: Mapped[list["Provision"]] = relationship(back_populates="status")

    history: Mapped[list["ProvisionStatusHistory"]] = relationship(
        back_populates="status"
    )


# =========================================================
# PROVISION
# =========================================================


class Provision(Base, AuditMixin):
    __tablename__ = "provisions"

    __table_args__ = (
        UniqueConstraint("company_id", "ticket_code"),
        Index("ix_provision_company_status", "company_id", "status_id"),
        {"schema": "finance"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    ticket_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    status_id: Mapped[int] = mapped_column(
        ForeignKey("finance.provision_statuses.id"), nullable=False, index=True
    )

    concept_id: Mapped[int] = mapped_column(
        ForeignKey("finance.provision_concepts.id"), nullable=False, index=True
    )

    area_id: Mapped[int] = mapped_column(
        ForeignKey("master.areas.id"), nullable=False, index=True
    )

    currency_id: Mapped[int] = mapped_column(
        ForeignKey("master.currencies.id"), nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Mejor usar Date para fecha contable
    provision_date: Mapped[date] = mapped_column(Date, nullable=False)

    observations: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Estado actual SAP
    sap_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("master.companies.id"), nullable=False, index=True
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    concept: Mapped["ProvisionConcept"] = relationship(back_populates="provisions")

    status: Mapped["ProvisionStatus"] = relationship(back_populates="provisions")

    documents: Mapped[list["ProvisionDocument"]] = relationship(
        back_populates="provision", cascade="all, delete-orphan"
    )

    status_history: Mapped[list["ProvisionStatusHistory"]] = relationship(
        back_populates="provision", cascade="all, delete-orphan"
    )

    sap_syncs: Mapped[list["ProvisionSAPSync"]] = relationship(
        back_populates="provision", cascade="all, delete-orphan"
    )


# =========================================================
# PROVISION DOCUMENT
# =========================================================


class ProvisionDocument(Base, AuditMixin):
    __tablename__ = "provision_documents"

    __table_args__ = (
        Index("ix_provision_document_provision", "provision_id"),
        {"schema": "finance"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    provision_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance.provisions.id"), nullable=False
    )

    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    supplier_tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    currency_id: Mapped[int] = mapped_column(
        ForeignKey("master.currencies.id"), nullable=False
    )

    # Relaciones
    provision: Mapped["Provision"] = relationship(back_populates="documents")


# =========================================================
# PROVISION STATUS HISTORY
# =========================================================


class ProvisionStatusHistory(Base, AuditMixin):
    __tablename__ = "provision_status_history"

    __table_args__ = (
        Index("ix_status_history_provision", "provision_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    provision_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance.provisions.id"), nullable=False
    )

    status_id: Mapped[int] = mapped_column(
        ForeignKey("finance.provision_statuses.id"), nullable=False
    )

    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("security.auth.id"), nullable=True
    )

    comments: Mapped[str | None] = mapped_column(String(500), nullable=True)

    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relaciones
    provision: Mapped["Provision"] = relationship(back_populates="status_history")

    status: Mapped["ProvisionStatus"] = relationship(back_populates="history")


# =========================================================
# PROVISION SAP SYNC
# =========================================================


class ProvisionSAPSync(Base, AuditMixin):
    __tablename__ = "provision_sap_syncs"

    __table_args__ = (
        Index("ix_sap_sync_provision", "provision_id"),
        {"schema": "finance"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    provision_id: Mapped[UUID] = mapped_column(
        ForeignKey("finance.provisions.id"), nullable=False
    )

    request_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    response_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    sap_document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # SUCCESS / ERROR / RETRY

    message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relaciones
    provision: Mapped["Provision"] = relationship(back_populates="sap_syncs")
