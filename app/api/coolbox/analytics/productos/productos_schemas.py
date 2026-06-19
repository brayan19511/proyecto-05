from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProductoABCItem(BaseModel):
    producto: str
    descripcion: Optional[str] = None
    marca: Optional[str] = None
    rubro: Optional[str] = None
    familia: Optional[str] = None
    venta_total: Decimal
    unidades_vendidas: int
    participacion: Decimal
    participacion_acumulada: Decimal
    clasificacion_abc: str


class ProductoTopItem(BaseModel):
    producto: str
    descripcion: Optional[str] = None
    marca: Optional[str] = None
    rubro: Optional[str] = None
    familia: Optional[str] = None
    venta_total: Decimal
    unidades_vendidas: int
    cantidad_documentos: int


class ProductoBajoMovimientoItem(BaseModel):
    producto: str
    descripcion: Optional[str] = None
    marca: Optional[str] = None
    rubro: Optional[str] = None
    familia: Optional[str] = None
    venta_total: Decimal
    unidades_vendidas: int
    cantidad_documentos: int


class ProductoResumenCategoriaItem(BaseModel):
    categoria: str
    venta_total: Decimal
    unidades_vendidas: int
    cantidad_productos: int


class ProductoFiltroItem(BaseModel):
    valor: str


class ProductosFiltrosResponse(BaseModel):
    rubros: list[ProductoFiltroItem]
    familias: list[ProductoFiltroItem]
    marcas: list[ProductoFiltroItem]
    subfamilias: list[ProductoFiltroItem]
