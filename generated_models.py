from typing import Optional
import datetime

from sqlalchemy import Boolean, DateTime, Index, PrimaryKeyConstraint, String, Unicode, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class MxRappiSku(Base):
    __tablename__ = 'mx_rappi_sku'
    __table_args__ = (
        PrimaryKeyConstraint('sku', name='PK__mx_rappi__DDDF4BE6ED1DAB23'),
        Index('UQ_mx_rappi_sku_id_rappi', 'id_rappi', mssql_clustered=False, mssql_where='([id_rappi] IS NOT NULL)', unique=True)
    )

    sku: Mapped[str] = mapped_column(Unicode(255, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True)
    id_rappi: Mapped[Optional[str]] = mapped_column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('((1))'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(getdate())'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(getdate())'))
