from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class VentasFiltros(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    canal: Optional[str] = None
    tienda: Optional[str] = None


class VentasKpisResponse(BaseModel):
    venta_total: Decimal
    cantidad_documentos: int
    unidades_vendidas: int
    ticket_promedio: Decimal
    descuento_total: Decimal
    clientes_unicos: int


class VentasEvolucionItem(BaseModel):
    fecha: date
    venta_total: Decimal
    cantidad_documentos: int
    unidades_vendidas: int
    ticket_promedio: Decimal


class VentasPorCanalItem(BaseModel):
    canal: str
    venta_total: Decimal
    cantidad_documentos: int
    unidades_vendidas: int
    participacion: Decimal


class VentasPorTiendaItem(BaseModel):
    tienda: str
    venta_total: Decimal
    cantidad_documentos: int
    unidades_vendidas: int
    ticket_promedio: Decimal


class TopProductoItem(BaseModel):
    producto: str
    descripcion: Optional[str] = None
    venta_total: Decimal
    unidades_vendidas: int
    cantidad_documentos: int