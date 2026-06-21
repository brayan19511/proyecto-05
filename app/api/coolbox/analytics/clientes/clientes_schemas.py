from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ClienteRfmItem(BaseModel):
    cliente: str
    ultima_compra: date
    recencia: int
    frecuencia: int
    monetario: Decimal
    score_recencia: int
    score_frecuencia: int
    score_monetario: int
    score_rfm: str
    segmento: str


class ClienteSegmentoItem(BaseModel):
    segmento: str
    cantidad_clientes: int
    venta_total: Decimal
    ticket_promedio: Decimal


class ClienteTopItem(BaseModel):
    cliente: str
    venta_total: Decimal
    cantidad_documentos: int
    ultima_compra: date


class ClienteFrecuenciaCompraItem(BaseModel):
    cliente: str
    cantidad_documentos: int
    primera_compra: date
    ultima_compra: date
    dias_entre_compras: Optional[Decimal] = None


class ClienteFiltroCanalItem(BaseModel):
    codigo: str
    nombre: str


class ClienteFiltroTiendaItem(BaseModel):
    codigo: str
    nombre: str


class ClientesFiltrosResponse(BaseModel):
    canales: list[ClienteFiltroCanalItem]
    tiendas: list[ClienteFiltroTiendaItem]
