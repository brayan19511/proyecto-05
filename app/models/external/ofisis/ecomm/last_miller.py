import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, PrimaryKeyConstraint, String, Unicode, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PeyaPromoSku(Base):
    __tablename__ = 'peya_promo_sku'
    __table_args__ = (
        PrimaryKeyConstraint('sku', name='PK__peya_pro__DDDF4BE6CC7A4B2A'),
    )

    sku: Mapped[str] = mapped_column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True)


class PeyaSku(Base):
    __tablename__ = 'peya_sku'
    __table_args__ = (
        PrimaryKeyConstraint('sku', name='PK__peya_sku__DDDF4BE6D4456D98'),
    )

    sku: Mapped[str] = mapped_column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True)
    id_peya: Mapped[Optional[str]] = mapped_column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('((1))'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(getdate())'))
    modified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(getdate())'))


class RappiSku(Base):
    __tablename__ = 'rappi_sku'
    __table_args__ = (
        PrimaryKeyConstraint('sku', name='PK__rappi_sk__DDDF4BE6E6F89925'),
    )

    sku: Mapped[str] = mapped_column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True)
    id_rappi: Mapped[Optional[str]] = mapped_column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(getdate())'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(getdate())'))



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
