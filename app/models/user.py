from typing import List, Optional, TYPE_CHECKING
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import String,  DateTime, ForeignKey, func, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db_postgres import Base

if TYPE_CHECKING:
    from .security import Auth

class Information(Base):
    __tablename__ = "information"
    __table_args__ = {"schema": "user"}

    # La PK es compartida (Foreign Key que también es Primary Key)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("security.auth.id"), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    lastname: Mapped[Optional[str]] = mapped_column(String)
    birthday: Mapped[Optional[date]] = mapped_column(Date)
    document_type: Mapped[Optional[str]] = mapped_column(String)
    document_number: Mapped[Optional[str]] = mapped_column(String, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    # Relación inversa hacia Auth
    auth: Mapped["Auth"] = relationship(back_populates="profile")
    
    @property
    def email(self) -> str:
        return self.auth.email if self.auth else ""