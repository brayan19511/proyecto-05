
from typing import List, Optional

from pydantic import BaseModel


class LibroMayorSap(BaseModel):
    fecha_contabilizacion: str
    fecha_documento: str
    numero_documento: str
    transaccion_id: int
    transaccion_tipo: str
    folio: str
    FolioPref: Optional[str]
    FolioNum: Optional[int]
    tipo_documento: str
    linea: int
    cuenta_asociada: str
    nombre_cuenta_asociada: str
    proveedor: str
    descripcion: str
    comentario_linea: str
    cuenta_contrapartida: str
    nombre_contrapartida: str
    referencia_1: str
    referencia_2: str
    referencia_3: str
    cargo_abono_ml: float
    cargo_abono_me: int
    usuario_id: int
    autor: str
    centro_costo: str
    centro_area: str
    nombre_area: Optional[str]
    fecha_creacion: str
    fecha_actualizacion: str
