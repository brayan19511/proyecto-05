"""Conversiones de valores de ICG a tipos que GraphQL entiende.

GraphQL solo conoce unos pocos tipos escalares (Int, Float, String, Boolean,
ID) mas los que agrega Strawberry (Date, DateTime, JSON...). Las columnas de
SQL Server llegan como Decimal, datetime o char con espacios, asi que aqui las
normalizamos antes de armar los tipos.

Cuatro convenciones de ICG que estos conversores resuelven. En ICG casi nada es
NULL: cada tipo tiene su propio valor de "sin dato".

| Tipo de columna | "Sin valor" en ICG | Conversor |
|---|---|---|
| Booleano | char 'T' / 'F' | `a_booleano` |
| Fecha | 1899-12-30 (el cero de fechas de Delphi) | `a_fecha` |
| Referencia numerica | -1 | `a_entero` |
| Atributo de texto | '.' (COLOR, TALLA) | `a_texto(..., vacios=("."))` |

Sin traducirlos, una linea que no abona a nada mostraria
`documentoOrigenNumero: -1` y un articulo sin color mostraria `color: "."`.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any


# ICG usa esta fecha como "sin valor" en lugar de NULL.
FECHA_VACIA_ICG = date(1899, 12, 30)

# Y este entero en las columnas de referencia (IDPROMOCION, ABONODE_*, ...).
ENTERO_VACIO_ICG = -1


def a_float(valor: Any) -> float:
    """Convierte Decimal/None a float. Los importes nulos valen 0."""
    if valor is None:
        return 0.0
    return float(valor)


def a_texto(valor: Any, *, vacios: tuple[str, ...] = ()) -> str | None:
    """Convierte cualquier valor a texto sin espacios sobrantes.

    Se usa en columnas donde el tipo real de ICG no es seguro (numericas en
    unas instalaciones, char en otras). Si confirmas el tipo de una columna,
    puedes cambiarla a int en el type y quitar esta conversion.

    `vacios` son textos que ICG usa como marcador de "sin dato" en esa columna
    y que conviene devolver como null. El caso tipico es el punto en COLOR y
    TALLA: `a_texto(fila.get("color"), vacios=("."))`.
    """
    if valor is None:
        return None

    texto = str(valor).strip()
    if not texto or texto in vacios:
        return None

    return texto


def a_entero(valor: Any, *, vacio: int | None = ENTERO_VACIO_ICG) -> int | None:
    """Convierte a entero, devolviendo None cuando es el valor vacio de ICG.

    ICG guarda -1 (no NULL ni 0) en las columnas que apuntan a otra cosa y no
    apuntan a nada: IDPROMOCION, ABONODE_NUMALBARAN, ABONODE_NUMLIN,
    IDMOTIVODTO, CONTACTO. Pasa `vacio=None` si la columna no usa centinela.
    """
    if valor is None:
        return None

    texto = str(valor).strip()
    if not texto:
        return None

    try:
        entero = int(float(texto))
    except ValueError:
        return None

    return None if vacio is not None and entero == vacio else entero


def a_booleano(valor: Any) -> bool:
    """Interpreta los booleanos de ICG: char 'T'/'F' o bit 1/0."""
    if valor is None:
        return False

    if isinstance(valor, bool):
        return valor

    if isinstance(valor, (int, float, Decimal)):
        return valor != 0

    return str(valor).strip().upper() in {"T", "S", "1", "TRUE"}


def a_hora(valor: Any) -> str | None:
    """Devuelve solo la hora como HH:MM:SS.

    ICG guarda las horas en columnas datetime con la fecha centinela
    1899-12-30, asi que el valor crudo se ve como "1899-12-30 15:22:29".
    """
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor.strftime("%H:%M:%S")

    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M:%S")

    return a_texto(valor)


def a_fecha(valor: Any) -> date | None:
    """Devuelve la fecha, o None si es la fecha vacia de ICG."""
    if valor is None:
        return None

    fecha = valor.date() if isinstance(valor, datetime) else valor
    if fecha == FECHA_VACIA_ICG:
        return None

    return fecha


def a_fecha_hora(valor: Any) -> datetime | None:
    """Igual que a_fecha pero conservando la hora (fechas de auditoria)."""
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return None if valor.date() == FECHA_VACIA_ICG else valor

    return None if valor == FECHA_VACIA_ICG else valor


def a_json(valor: Any) -> Any:
    """Deja el valor listo para viajar dentro del campo JSON camposExtra.

    Decimal y datetime no son serializables a JSON, asi que se traducen. El
    resto de tipos (int, float, str, bool, None) pasa tal cual.
    """
    if valor is None or isinstance(valor, (bool, int, float, str)):
        return valor

    if isinstance(valor, Decimal):
        return float(valor)

    if isinstance(valor, datetime):
        if valor.date() == FECHA_VACIA_ICG:
            return valor.strftime("%H:%M:%S")
        return valor.isoformat()

    if isinstance(valor, date):
        return None if valor == FECHA_VACIA_ICG else valor.isoformat()

    if isinstance(valor, bytes):
        return valor.hex()

    return str(valor).strip()
