"""DataLoaders: la pieza que evita el problema N+1.

EL PROBLEMA
Si el cliente pide 100 documentos y cada uno resuelve sus lineas por separado,
se ejecutan 100 consultas (el famoso "N+1"). Con 3 niveles de relaciones eso
son miles de consultas y la API se cae.

LA SOLUCION
Un DataLoader junta todas las claves que se pidieron en el mismo instante y
llama UNA vez al repositorio con la lista completa. 100 documentos -> 1 consulta.

COMO SE ESCRIBE UN LOADER
La funcion de lote recibe una lista de claves y debe devolver una lista de
resultados en EL MISMO ORDEN y con LA MISMA CANTIDAD que las claves. Si una
clave no tiene datos se devuelve None (o [] cuando la relacion es una lista).

POR QUE EL CANDADO (anyio.Lock)
Los metodos del repositorio son sincronos, asi que se ejecutan en un hilo
aparte para no bloquear el event loop. Pero una sesion de SQLAlchemy no es
segura entre hilos: si dos loaders consultaran a la vez sobre la misma sesion,
se corromperia. El candado garantiza una consulta a la vez por request.
"""

from dataclasses import dataclass
from functools import partial
from typing import Any, Callable

import anyio
from strawberry.dataloader import DataLoader

from app.api.graphql.repository import Fila, IcgGraphRepository


class EjecutorDb:
    """Ejecuta funciones sincronas del repositorio desde codigo asincrono."""

    def __init__(self) -> None:
        self._candado = anyio.Lock()

    async def ejecutar(self, funcion: Callable, argumento: Any) -> Any:
        async with self._candado:
            return await anyio.to_thread.run_sync(funcion, argumento)


@dataclass
class Loaders:
    """Todos los loaders de un request. Se crean nuevos en cada request."""

    lineas: DataLoader
    tesoreria: DataLoader
    campos_libres_albaran: DataLoader
    campos_libres_factura: DataLoader
    tipo_doc: DataLoader
    articulo: DataLoader
    marca: DataLoader
    seccion: DataLoader
    familia: DataLoader
    subfamilia: DataLoader


def construir_loaders(repo: IcgGraphRepository, contexto: dict) -> Loaders:
    """Arma los loaders del request.

    Recibe el contexto porque el loader de lineas necesita saber que columnas
    extra pidio el cliente, y eso lo fija el query raiz despues de que el
    contexto ya existe. Se lee en el momento del lote, no ahora.
    """
    ejecutor = EjecutorDb()

    def loader_de_lista(metodo: Callable) -> DataLoader:
        """Para relaciones 1:N (un documento tiene muchas lineas)."""

        async def cargar(claves: list) -> list[list[Fila]]:
            agrupado = await ejecutor.ejecutar(metodo, list(claves))
            return [agrupado.get(clave, []) for clave in claves]

        return DataLoader(load_fn=cargar)

    def loader_de_uno(metodo: Callable) -> DataLoader:
        """Para relaciones N:1 (muchas lineas apuntan a un articulo)."""

        async def cargar(claves: list) -> list[Fila | None]:
            agrupado = await ejecutor.ejecutar(metodo, list(claves))
            return [agrupado.get(clave) for clave in claves]

        return DataLoader(load_fn=cargar)

    async def cargar_lineas(claves: list) -> list[list[Fila]]:
        # Las columnas extra son las mismas para todo el request, asi que
        # alcanza con leerlas del contexto cuando se dispara el lote.
        columnas = contexto.get("columnas_linea") or []
        agrupado = await ejecutor.ejecutar(
            partial(repo.lineas_por_documento, columnas_extra=columnas),
            list(claves),
        )
        return [agrupado.get(clave, []) for clave in claves]

    return Loaders(
        lineas=DataLoader(load_fn=cargar_lineas),
        tesoreria=loader_de_lista(repo.tesoreria_por_factura),
        campos_libres_albaran=loader_de_uno(
            repo.campos_libres_albaran_por_documento
        ),
        campos_libres_factura=loader_de_uno(
            repo.campos_libres_factura_por_documento
        ),
        tipo_doc=loader_de_uno(repo.tipos_doc_por_codigo),
        articulo=loader_de_uno(repo.articulos_por_codigo),
        marca=loader_de_uno(repo.marcas_por_codigo),
        seccion=loader_de_uno(repo.secciones_por_clave),
        familia=loader_de_uno(repo.familias_por_clave),
        subfamilia=loader_de_uno(repo.subfamilias_por_clave),
    )
