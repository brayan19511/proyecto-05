"""Queries raiz: los puntos de entrada del schema.

Un cliente no puede empezar por cualquier tipo, solo por los campos que estan
declarados aqui. Desde ahi navega el grafo con las relaciones definidas en
types/.

REGLAS DE UN QUERY RAIZ EN ESTE PROYECTO
1. Rango de fechas obligatorio, salvo que se pidan documentos por clave exacta
   (ahi ya esta acotado). Es la proteccion para que nadie barra ICG completo.
2. Limite con techo duro. El cliente puede pedir menos, nunca mas.
3. Permiso declarado con permission_classes.
4. Sin SQL: se llama al repositorio del contexto.

COMO CRECER SIN COMPLICARSE
Cuando este archivo tenga muchos campos, se parte en varios tipos y se unen
por herencia, que es la forma que da Strawberry para combinar queries:

    @strawberry.type
    class Query(QueryIcg, QueryCompras):
        pass
"""

from datetime import date
from typing import Annotated

import strawberry

from app.api.graphql.columnas import CABECERA, LINEA
from app.api.graphql.permissions import RequierePermisoIcg
from app.api.graphql.types.documento import DocumentoVenta


# Techo duro de filas por consulta. Si alguien pide 10000 se le entregan 500.
LIMITE_MAXIMO = 500
LIMITE_POR_DEFECTO = 100

# Rango maximo permitido en dias, para no barrer anios de historia.
RANGO_MAXIMO_DIAS = 31

# Tope de valores en el filtro de tipos de documento (ICG tiene pocas decenas).
MAXIMO_TIPOS_DOC = 50

# Tope de documentos pedidos por clave exacta, para acotar el tamanio del SQL.
MAXIMO_DOCUMENTOS = 100


@strawberry.input(
    description=(
        "Clave de un documento de ICG. La serie sola no identifica nada: hay "
        "que indicar numalbaran (numero de albaran) o numfac (numero de "
        "factura), porque son numeraciones distintas. Si se indican los dos, "
        "el documento tiene que cumplir ambos."
    )
)
class ClaveDocumento:
    numserie: str
    numalbaran: int | None = None
    numfac: int | None = None

    def como_tupla(self) -> tuple[str, int | None, int | None]:
        """Convierte a la tupla que espera el repositorio.

        El repositorio no conoce los tipos de GraphQL: recibe tuplas simples.
        """
        return (self.numserie.strip(), self.numalbaran, self.numfac)


def _validar_filtros(
    *,
    desde: date | None,
    hasta: date | None,
    claves: list[tuple],
    tipodoc: list[int] | None,
) -> None:
    """Valida los filtros antes de tocar la base.

    Es una funcion de modulo y no un metodo: en los resolvers raiz `self` es el
    root value del schema (None), asi que no se puede llamar a metodos de Query
    desde dentro de un resolver.
    """
    hay_rango = desde is not None and hasta is not None

    if not hay_rango and not claves:
        raise ValueError("Indica desde y hasta, o una lista de documentos")

    if hay_rango:
        if hasta < desde:
            raise ValueError("El parametro hasta no puede ser menor que desde")

        if (hasta - desde).days > RANGO_MAXIMO_DIAS:
            raise ValueError(
                f"El rango no puede superar {RANGO_MAXIMO_DIAS} dias"
            )

    if len(claves) > MAXIMO_DOCUMENTOS:
        raise ValueError(
            f"No se pueden pedir mas de {MAXIMO_DOCUMENTOS} documentos"
        )

    for numserie, numalbaran, numfac in claves:
        if not numserie:
            raise ValueError("Cada documento necesita numserie")

        if numalbaran is None and numfac is None:
            raise ValueError(
                f"El documento de la serie {numserie} necesita numalbaran "
                "o numfac: son numeraciones distintas y no se pueden adivinar"
            )

    if tipodoc is not None and len(tipodoc) > MAXIMO_TIPOS_DOC:
        raise ValueError(
            f"No se pueden pedir mas de {MAXIMO_TIPOS_DOC} tipos de documento"
        )


@strawberry.type
class Query:
    @strawberry.field(
        permission_classes=[RequierePermisoIcg],
        description=(
            "Columnas de ALBVENTACAB que se pueden pedir con el argumento "
            "`columnas` de documentosVenta. Las que ya tienen campo propio no "
            "aparecen en esta lista."
        ),
    )
    def columnas_documento_venta(self) -> list[str]:
        return CABECERA.disponibles()

    @strawberry.field(
        permission_classes=[RequierePermisoIcg],
        description=(
            "Columnas de ALBVENTALIN que se pueden pedir con el argumento "
            "`columnasLinea` de documentosVenta."
        ),
    )
    def columnas_linea_venta(self) -> list[str]:
        return LINEA.disponibles()

    @strawberry.field(
        permission_classes=[RequierePermisoIcg],
        description=(
            "Documentos de venta de ICG (ALBVENTACAB). Se filtra por rango de "
            "fechas o por una lista de documentos. Las relaciones (lineas, "
            "articulo, tesoreria, campos libres) solo consultan la base si se "
            "piden en la consulta."
        ),
    )
    def documentos_venta(
        self,
        info: strawberry.Info,
        desde: Annotated[
            date | None,
            strawberry.argument(
                description="Obligatorio salvo que se pase `documentos`."
            ),
        ] = None,
        hasta: Annotated[
            date | None,
            strawberry.argument(
                description="Obligatorio salvo que se pase `documentos`."
            ),
        ] = None,
        documentos: Annotated[
            list[ClaveDocumento] | None,
            strawberry.argument(
                description=(
                    "Documentos puntuales por clave, por ejemplo "
                    "[{numserie: \"001\", numalbaran: 1}]. Cuando se usa, el "
                    "rango de fechas es opcional."
                )
            ),
        ] = None,
        tienda: Annotated[
            str | None,
            strawberry.argument(
                description="CODALMACEN. Esta en la linea, no en la cabecera."
            ),
        ] = None,
        tipodoc: Annotated[
            list[int] | None,
            strawberry.argument(
                description=(
                    "Uno o varios tipos de documento, por ejemplo [5, 13] para "
                    "boletas y facturas o [17, 18] para notas de credito. "
                    "Vacio u omitido trae todos los tipos."
                )
            ),
        ] = None,
        pedido: Annotated[
            str | None,
            strawberry.argument(
                description=(
                    "Numero de pedido. Busca en NRO_PEDIDO (campos libres de "
                    "la factura) y en PEDIDOVTEX (campos libres del albaran)."
                )
            ),
        ] = None,
        canal_venta: Annotated[
            str | None,
            strawberry.argument(
                description=(
                    "CANAL_VENTA de los campos libres de la factura. "
                    "No distingue mayusculas ni espacios."
                )
            ),
        ] = None,
        columnas: Annotated[
            list[str] | None,
            strawberry.argument(
                description=(
                    "Columnas adicionales de ALBVENTACAB que llegan en el "
                    "campo camposExtra, por ejemplo [\"SALA\", \"MESA\"]. "
                    "Consulta columnasDocumentoVenta para ver la lista."
                )
            ),
        ] = None,
        columnas_linea: Annotated[
            list[str] | None,
            strawberry.argument(
                description=(
                    "Columnas adicionales de ALBVENTALIN que llegan en el "
                    "camposExtra de cada linea. Aplica a todas las lineas de "
                    "la consulta. Consulta columnasLineaVenta para la lista."
                )
            ),
        ] = None,
        limite: int = LIMITE_POR_DEFECTO,
    ) -> list[DocumentoVenta]:
        claves = [clave.como_tupla() for clave in documentos or []]

        _validar_filtros(
            desde=desde,
            hasta=hasta,
            claves=claves,
            tipodoc=tipodoc,
        )

        # Lista blanca: si el cliente inventa un nombre, falla aqui y nunca
        # llega al SQL.
        columnas_extra = CABECERA.validar(columnas or [])

        # Las columnas extra de linea las consume el loader de lineas, que se
        # dispara despues de este resolver, asi que viajan por el contexto.
        info.context["columnas_linea"] = LINEA.validar(columnas_linea or [])

        filas = info.context["repo"].documentos(
            desde=desde,
            hasta=hasta,
            claves=claves or None,
            tienda=tienda,
            tipodoc=tipodoc,
            pedido=pedido,
            canal_venta=canal_venta,
            columnas_extra=columnas_extra,
            limite=max(1, min(limite, LIMITE_MAXIMO)),
        )

        return [
            DocumentoVenta.desde_fila(fila, columnas_extra=columnas_extra)
            for fila in filas
        ]
