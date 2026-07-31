from datetime import date
from typing import Annotated, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    computed_field,
    field_validator,
)

from app.api.finance.libro_mayor.constants import SUPPORTED_ACCOUNTS


def _validar_cuenta(value: str) -> str:
    if value not in SUPPORTED_ACCOUNTS:
        raise ValueError("Cuenta soportada: 95 o 97")
    return value


# Tipo reutilizable: valida que la cuenta sea una de las soportadas (95/97).
AccountCode = Annotated[str, AfterValidator(_validar_cuenta)]

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



class LibroMayorResponse(BaseModel):
    # Configuración obligatoria para leer desde SQLAlchemy en Pydantic v2
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,  # Permite usar los alias correctamente
    }

    tiene_id: bool = Field(alias="tiene_regla")
    subcodigo: Optional[str] = Field(alias="subcodigo")  # Puede ser Null
    codigo: str = Field(alias="codigo")
    nombre_cuenta: str = Field(alias="nombre_cuenta")
    tipo_cuenta: str = Field(alias="tipo_cuenta")
    cuenta: str = Field(alias="cuenta_asociada")
    fecha_contabilizacion: date = Field(alias="fecha_contabilizacion")
    fecha_documento: date = Field(alias="fecha_documento")
    numero_documento: str = Field(alias="numero_documento")

    # CORREGIDO: En tu BD es BIGINT, por lo tanto aquí debe ser int
    transaccion_id: int = Field(alias="transaccion_id")

    folio: Optional[str] = Field(alias="folio")
    tipo_documento: Optional[str] = Field(alias="tipo_documento")
    linea: int = Field(alias="linea")
    nombre_cuenta_asociada: str = Field(alias="nombre_cuenta_asociada")
    proveedor: Optional[str] = Field(alias="proveedor")
    descripcion: Optional[str] = Field(alias="descripcion")
    comentario_linea: Optional[str] = Field(alias="comentario_linea")
    cuenta_contrapartida: Optional[str] = Field(alias="cuenta_contrapartida")
    nombre_contrapartida: Optional[str] = Field(alias="nombre_contrapartida")
    referencia_1: Optional[str] = Field(alias="referencia_1")
    referencia_2: Optional[str] = Field(alias="referencia_2")
    referencia_3: Optional[str] = Field(alias="referencia_3")
    importe_soles: float = Field(alias="cargo_abono_ml")
    importe_dolares: float = Field(alias="cargo_abono_me")
    centro_costo: Optional[str] = Field(alias="centro_costo")
    centro_area: Optional[str] = Field(alias="centro_area")
    nombre_area: Optional[str] = Field(alias="nombre_area")

    @computed_field
    @property
    def mes(self) -> Optional[int]:
        return self.fecha_contabilizacion.month if self.fecha_contabilizacion else None

    @computed_field
    @property
    def nmes(
        self,
    ) -> Optional[str]:  # Cambiado a str porque devuelve "Enero", "Febrero", etc.
        if self.fecha_contabilizacion:
            meses = {
                1: "Enero",
                2: "Febrero",
                3: "Marzo",
                4: "Abril",
                5: "Mayo",
                6: "Junio",
                7: "Julio",
                8: "Agosto",
                9: "Septiembre",
                10: "Octubre",
                11: "Noviembre",
                12: "Diciembre",
            }
            return meses.get(self.fecha_contabilizacion.month, None)
        return None

    @computed_field
    @property
    def anio(self) -> Optional[int]:
        return self.fecha_contabilizacion.year if self.fecha_contabilizacion else None


class SyncRequest(BaseModel):
    account: AccountCode
    start_date: date
    end_date: date


class SyncDeltaRequest(BaseModel):
    account: AccountCode
    start_date: date | None = None
    end_date: date | None = None


class ReprocessDateRangeRequest(BaseModel):
    account: AccountCode
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, end_date: date, info):
        start_date = info.data.get("start_date")

        if start_date and end_date < start_date:
            raise ValueError(
                "La fecha fin no puede ser menor a la fecha inicio"
            )

        return end_date
    
    
    
    

class ReglaGastoCreate(BaseModel):
    
    tipo_regla: str
    prioridad: int
    codigo: str
    subcodigo: str | None = None
    nombre_cuenta: str

    cuenta: str | None = None
    cuenta_contrapartida: str | None = None
    centro_costo: str | None = None

    filtro_texto: str | None = None
    texto_excluido: str | None = None

    monto_min: float | None = None
    monto_max: float | None = None

    activo: bool = True
class ReglaGastoUpdate(BaseModel):

    prioridad: int | None = None
    codigo: str | None = None
    subcodigo: str | None = None
    nombre_cuenta: str | None = None

    cuenta: str | None = None
    cuenta_contrapartida: str | None = None
    centro_costo: str | None = None

    filtro_texto: str | None = None
    texto_excluido: str | None = None

    monto_min: float | None = None
    monto_max: float | None = None

    activo: bool | None = None
    
    
# libro_mayor_schema.py

class LibroMayorResumenResponse(BaseModel):
    anio: int
    mes: int
    codigo: str | None
    subcodigo: str | None
    nombre_cuenta: str | None
    proveedor: str | None

    cantidad_registros: int

    importe_soles: float
    importe_dolares: float