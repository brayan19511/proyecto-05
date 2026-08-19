"""Tipos GraphQL de los maestros de articulo de ICG.

COMO LEER ESTE ARCHIVO (es el patron de todo el modulo):

- Cada clase con @strawberry.type es un "tipo" del schema GraphQL.
- Los atributos normales (numserie: str) son campos que salen directo de la
  fila que trajo el repositorio.
- Los metodos con @strawberry.field son RELACIONES: su codigo solo se ejecuta
  si el cliente pide ese campo en su consulta. Si no lo pide, no hay consulta
  a la base. Ese es el beneficio principal de GraphQL frente a un SELECT con
  muchos JOIN que siempre trae todo.
- `desde_fila` es un constructor: recibe el dict del repositorio y arma el tipo.
  Lo hacemos explicito (en vez de **fila) para que se vea que columna alimenta
  cada campo.
- Strawberry convierte los nombres a camelCase en el schema:
  `total_neto` en Python se consulta como `totalNeto` en GraphQL.
"""

import strawberry

from app.api.graphql.converters import a_texto
from app.api.graphql.repository import Fila


@strawberry.type(description="Marca comercial del articulo (tabla MARCA)")
class Marca:
    codmarca: str | None
    descripcion: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "Marca":
        return cls(
            codmarca=a_texto(fila.get("codmarca")),
            descripcion=a_texto(fila.get("descripcion")),
        )


@strawberry.type(description="Seccion del articulo (tabla SECCIONES)")
class Seccion:
    dpto: str | None
    seccion: str | None
    descripcion: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "Seccion":
        return cls(
            dpto=a_texto(fila.get("numdpto")),
            seccion=a_texto(fila.get("numseccion")),
            descripcion=a_texto(fila.get("descripcion")),
        )


@strawberry.type(description="Familia del articulo (tabla FAMILIAS)")
class Familia:
    dpto: str | None
    seccion: str | None
    familia: str | None
    descripcion: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "Familia":
        return cls(
            dpto=a_texto(fila.get("numdpto")),
            seccion=a_texto(fila.get("numseccion")),
            familia=a_texto(fila.get("numfamilia")),
            descripcion=a_texto(fila.get("descripcion")),
        )


@strawberry.type(description="Subfamilia del articulo (tabla SUBFAMILIAS)")
class Subfamilia:
    dpto: str | None
    seccion: str | None
    familia: str | None
    subfamilia: str | None
    descripcion: str | None

    @classmethod
    def desde_fila(cls, fila: Fila) -> "Subfamilia":
        return cls(
            dpto=a_texto(fila.get("numdpto")),
            seccion=a_texto(fila.get("numseccion")),
            familia=a_texto(fila.get("numfamilia")),
            subfamilia=a_texto(fila.get("numsubfamilia")),
            descripcion=a_texto(fila.get("descripcion")),
        )


@strawberry.type(description="Articulo de ICG (tabla ARTICULOS)")
class Articulo:
    codarticulo: str
    descripcion: str | None
    referencia: str | None
    descatalogado: str | None

    # strawberry.Private = dato interno que NO aparece en el schema.
    # Lo guardamos porque las relaciones de abajo lo necesitan como clave,
    # pero el cliente no tiene por que verlo.
    dpto: strawberry.Private[object]
    cod_seccion: strawberry.Private[object]
    cod_familia: strawberry.Private[object]
    cod_subfamilia: strawberry.Private[object]
    cod_marca: strawberry.Private[object]

    @classmethod
    def desde_fila(cls, fila: Fila) -> "Articulo":
        return cls(
            codarticulo=a_texto(fila.get("codarticulo")) or "",
            descripcion=a_texto(fila.get("descripcion")),
            referencia=a_texto(fila.get("refproveedor")),
            descatalogado=a_texto(fila.get("descatalogado")),
            dpto=fila.get("dpto"),
            cod_seccion=fila.get("seccion"),
            cod_familia=fila.get("familia"),
            cod_subfamilia=fila.get("subfamilia"),
            cod_marca=fila.get("marca"),
        )

    # -----------------------------------------------------------------
    # RELACIONES (cada una es un LEFT JOIN de la consulta original)
    # -----------------------------------------------------------------
    @strawberry.field(description="LEFT JOIN MARCA")
    async def marca(self, info: strawberry.Info) -> Marca | None:
        if self.cod_marca is None:
            return None

        fila = await info.context["loaders"].marca.load(self.cod_marca)
        return Marca.desde_fila(fila) if fila else None

    @strawberry.field(description="LEFT JOIN SECCIONES")
    async def seccion(self, info: strawberry.Info) -> Seccion | None:
        if self.dpto is None or self.cod_seccion is None:
            return None

        clave = (self.dpto, self.cod_seccion)
        fila = await info.context["loaders"].seccion.load(clave)
        return Seccion.desde_fila(fila) if fila else None

    @strawberry.field(description="LEFT JOIN FAMILIAS")
    async def familia(self, info: strawberry.Info) -> Familia | None:
        if self.dpto is None or self.cod_seccion is None or self.cod_familia is None:
            return None

        clave = (self.dpto, self.cod_seccion, self.cod_familia)
        fila = await info.context["loaders"].familia.load(clave)
        return Familia.desde_fila(fila) if fila else None

    @strawberry.field(description="LEFT JOIN SUBFAMILIAS")
    async def subfamilia(self, info: strawberry.Info) -> Subfamilia | None:
        if (
            self.dpto is None
            or self.cod_seccion is None
            or self.cod_familia is None
            or self.cod_subfamilia is None
        ):
            return None

        clave = (
            self.dpto,
            self.cod_seccion,
            self.cod_familia,
            self.cod_subfamilia,
        )
        fila = await info.context["loaders"].subfamilia.load(clave)
        return Subfamilia.desde_fila(fila) if fila else None
