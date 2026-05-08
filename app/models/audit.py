# app/models/audit.py

import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    ForeignKey,
    Float,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_postgres import Base


# =========================================================
# TABLA PRINCIPAL
# =========================================================

class AuditLog(Base):
    __tablename__ = "logs"
    __table_args__ = {"schema": "audit"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Correlación entre servicios/request
    trace_id = Column(String(100), index=True, nullable=False)

    # Información del usuario
    user_id = Column(UUID(as_uuid=True), nullable=True)

    # Información HTTP
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    # Entorno
    environment = Column(String(20), nullable=True)
    # dev / staging / prod

    # Resultado HTTP
    status_code = Column(Integer, nullable=True)

    # Duración
    duration_ms = Column(Float, nullable=True)

    # Cliente
    ip_address = Column(String(50), nullable=True)

    user_agent = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(
        DateTime(timezone=True), 
        nullable=False
    )

    finished_at = Column(
        DateTime(timezone=True), 
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), # Deja que la DB lo ponga al insertar
        nullable=False
    )

    # Relaciones
    detail = relationship(
        "AuditLogDetail",
        back_populates="log",
        uselist=False,
        cascade="all, delete-orphan"
    )

    steps = relationship(
        "AuditStep",
        back_populates="log",
        cascade="all, delete-orphan",
        order_by="AuditStep.step_order"
    )


# =========================================================
# DETALLE PESADO
# =========================================================

class AuditLogDetail(Base):
    __tablename__ = "log_details"
    __table_args__ = {"schema": "audit"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    log_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit.logs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # =========================
    # REQUEST
    # =========================

    request_headers = Column(JSON, nullable=True)

    query_params = Column(JSON, nullable=True)

    path_params = Column(JSON, nullable=True)

    request_body = Column(JSON, nullable=True)

    # =========================
    # RESPONSE
    # =========================

    response_headers = Column(JSON, nullable=True)

    response_body = Column(JSON, nullable=True)

    response_size_bytes = Column(Integer, nullable=True)

    # =========================
    # ERRORES
    # =========================

    level = Column(
        String(20),
        default="INFO",
        nullable=False
    )
    # INFO / WARNING / ERROR / CRITICAL

    error_message = Column(Text, nullable=True)

    error_stack = Column(Text, nullable=True)

    # =========================
    # RELACIÓN
    # =========================

    log = relationship(
        "AuditLog",
        back_populates="detail"
    )


# =========================================================
# PASOS INTERNOS
# =========================================================

class AuditStep(Base):
    __tablename__ = "log_steps"
    __table_args__ = {"schema": "audit"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    log_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit.logs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Orden del paso
    step_order = Column(Integer, nullable=False)

    # Nombre técnico del paso
    step_name = Column(String(100), nullable=False)
    # VALIDATE_TOKEN
    # LOAD_USER
    # SAVE_ORDER

    # Nivel
    status = Column(
        String(20),
        default="INFO",
        nullable=False
    )
    # INFO / WARNING / ERROR

    # Mensaje descriptivo
    message = Column(Text, nullable=True)

    # Tiempo del paso
    duration_ms = Column(Float, nullable=True)

    # Datos extra
    extra_data = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relación
    log = relationship(
        "AuditLog",
        back_populates="steps"
    )