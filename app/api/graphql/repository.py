"""Acceso a datos de ICG (SQL Server) para el modulo GraphQL.

REGLA DEL MODULO: todo el SQL vive en este archivo. Los resolvers de GraphQL
nunca ejecutan consultas, solo llaman metodos de aqui.

Los metodos tienen dos formas:

1. `documentos(...)`  -> lista de filas. Es el punto de entrada, siempre con
   filtro de fechas y un limite.
2. `*_por_*(claves)`  -> recibe una LISTA de claves y devuelve un diccionario
   indexado por esa clave. Ese formato es el que necesitan los DataLoaders
   para traer N registros con UNA sola consulta (ver loaders.py).

Nota sobre claves compuestas: SQL Server no soporta
`WHERE (a, b) IN ((1,2), (3,4))`, asi que filtramos con un IN por columna
(trae algunas filas de mas) y descartamos en Python las combinaciones que no
se pidieron. Es simple y suficientemente rapido para lotes de 100-500 claves.
"""

from datetime import date
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.api.graphql.columnas import COLUMNAS_BASE, COLUMNAS_LINEA_BASE


Fila = dict[str, Any]

# Clave de un documento: (numserie, numalbaran, numfac). numalbaran y numfac
# pueden venir en None; al menos uno de los dos tiene que traer valor.
ClaveDocumento = tuple[str, int | None, Any]


class IcgGraphRepository:
    def __init__(self, db_icg: Session):
        self.db_icg = db_icg

    # =====================================================================
    # PUNTO DE ENTRADA: cabeceras de venta (ALBVENTACAB)
    # =====================================================================
    def documentos(
        self,
        *,
        desde: date | None = None,
        hasta: date | None = None,
        claves: list[ClaveDocumento] | None = None,
        tienda: str | None = None,
        tipodoc: list[int] | None = None,
        pedido: str | None = None,
        canal_venta: str | None = None,
        columnas_extra: list[str] | None = None,
        limite: int = 100,
    ) -> list[Fila]:
        """Cabeceras de venta filtradas.

        Hay que pasar rango de fechas o `claves` (o ambos): sin ninguno de los
        dos la consulta barreria toda la tabla.

        COMO SE AGREGA UN FILTRO: se suma una condicion a `condiciones` y su
        valor a `params`. Nunca se interpola un valor dentro del SQL, solo
        fragmentos fijos escritos aqui.

        Cuando el filtro es por una columna que NO esta en ALBVENTACAB (por
        ejemplo el numero de pedido, que vive en las tablas de campos libres),
        se usa un EXISTS. Asi el filtro no cambia la cantidad de filas que
        devuelve la consulta ni obliga a traer esas tablas cuando el cliente
        no las pidio.
        """
        condiciones: list[str] = []
        params: dict[str, Any] = {"limite": limite}
        # Parametros que reciben una lista y se vuelven un IN (?, ?, ?).
        expandibles: list[str] = []

        if desde is not None and hasta is not None:
            condiciones.append("c.FECHA >= :desde")
            condiciones.append("c.FECHA < DATEADD(day, 1, :hasta)")
            params["desde"] = desde
            params["hasta"] = hasta

        if claves:
            # Un bloque por documento, unidos con OR. SQL Server no soporta
            # WHERE (a, b) IN ((...)), asi que se escribe la comparacion
            # completa de cada clave. Lo unico que se interpola es el indice
            # (un entero de enumerate), nunca un valor del cliente.
            bloques = []
            for indice, (numserie, numalbaran, numfac) in enumerate(claves):
                partes = [f"c.NUMSERIE = :doc{indice}_serie"]
                params[f"doc{indice}_serie"] = numserie

                if numalbaran is not None:
                    partes.append(f"c.NUMALBARAN = :doc{indice}_alb")
                    params[f"doc{indice}_alb"] = numalbaran

                if numfac is not None:
                    partes.append(f"c.NUMFAC = :doc{indice}_fac")
                    params[f"doc{indice}_fac"] = numfac

                bloques.append("(" + " AND ".join(partes) + ")")

            condiciones.append("(" + " OR ".join(bloques) + ")")

        if not condiciones:
            raise ValueError(
                "Se requiere rango de fechas o una lista de documentos"
            )

        if tipodoc:
            condiciones.append("c.TIPODOC IN :tipodoc")
            params["tipodoc"] = list(tipodoc)
            expandibles.append("tipodoc")

        if tienda is not None:
            # La tienda (CODALMACEN) esta en la linea, no en la cabecera.
            condiciones.append(
                "EXISTS ("
                " SELECT 1 FROM ALBVENTALIN l WITH (NOLOCK)"
                " WHERE l.NUMSERIE = c.NUMSERIE"
                " AND l.NUMALBARAN = c.NUMALBARAN"
                " AND l.CODALMACEN = :tienda"
                ")"
            )
            params["tienda"] = tienda

        if pedido is not None:
            # El numero de pedido vive en dos tablas segun el canal:
            # NRO_PEDIDO en los campos libres de la factura y PEDIDOVTEX en
            # los del albaran. Se busca en ambas, igual que hace la capa silver.
            condiciones.append(
                "("
                " EXISTS ("
                "  SELECT 1 FROM FACTURASVENTACAMPOSLIBRES fp WITH (NOLOCK)"
                "  WHERE fp.NUMSERIE = c.NUMSERIE"
                "  AND fp.NUMFACTURA = c.NUMFAC"
                "  AND fp.NRO_PEDIDO = :pedido"
                " ) OR EXISTS ("
                "  SELECT 1 FROM ALBVENTACAMPOSLIBRES ap WITH (NOLOCK)"
                "  WHERE ap.NUMSERIE = c.NUMSERIE"
                "  AND ap.NUMALBARAN = c.NUMALBARAN"
                "  AND ap.PEDIDOVTEX = :pedido"
                " )"
                ")"
            )
            params["pedido"] = pedido

        if canal_venta is not None:
            condiciones.append(
                "EXISTS ("
                " SELECT 1 FROM FACTURASVENTACAMPOSLIBRES fc WITH (NOLOCK)"
                " WHERE fc.NUMSERIE = c.NUMSERIE"
                " AND fc.NUMFACTURA = c.NUMFAC"
                " AND UPPER(LTRIM(RTRIM(fc.CANAL_VENTA))) = :canal_venta"
                ")"
            )
            params["canal_venta"] = canal_venta.strip().upper()

        where = " AND ".join(condiciones)

        # El SELECT sale del catalogo (columnas.py), no de una lista escrita a
        # mano aqui. Las columnas extra ya pasaron por la lista blanca de
        # validar_columnas, asi que son nombres de nuestro propio codigo.
        columnas = list(COLUMNAS_BASE) + list(columnas_extra or [])
        seleccion = ",\n                ".join(f"c.{columna}" for columna in columnas)

        return self._ejecutar(
            f"""
            SELECT TOP (:limite)
                {seleccion}
            FROM ALBVENTACAB c WITH (NOLOCK)
            WHERE {where}
            ORDER BY c.FECHA DESC, c.NUMSERIE, c.NUMALBARAN
            """,
            params,
            expandibles=tuple(expandibles),
        )

    # =====================================================================
    # RELACIONES DEL DOCUMENTO
    # =====================================================================
    def lineas_por_documento(
        self,
        claves: list[tuple[str, int]],
        *,
        columnas_extra: list[str] | None = None,
    ) -> dict[tuple[str, int], list[Fila]]:
        """ALBVENTALIN. Clave: (numserie, numalbaran). Un documento tiene N lineas."""
        columnas = list(COLUMNAS_LINEA_BASE) + list(columnas_extra or [])
        seleccion = ",\n                ".join(f"l.{columna}" for columna in columnas)

        filas = self._ejecutar(
            f"""
            SELECT
                {seleccion}
            FROM ALBVENTALIN l WITH (NOLOCK)
            WHERE l.NUMSERIE IN :serie_0
              AND l.NUMALBARAN IN :serie_1
            ORDER BY l.NUMSERIE, l.NUMALBARAN, l.NUMLIN
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1"),
        )
        return self._agrupar_lista(filas, ("numserie", "numalbaran"), claves)

    def tesoreria_por_factura(
        self,
        claves: list[tuple[str, Any]],
    ) -> dict[tuple[str, Any], list[Fila]]:
        """TESORERIA. Clave: (numserie, numfac). Une por SERIE / NUMERO."""
        filas = self._ejecutar(
            """
            SELECT
                t.SERIE,
                t.NUMERO,
                t.CODFORMAPAGO,
                t.IMPORTE
            FROM TESORERIA t WITH (NOLOCK)
            WHERE t.SERIE IN :serie_0
              AND t.NUMERO IN :serie_1
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1"),
        )
        return self._agrupar_lista(filas, ("serie", "numero"), claves)

    def campos_libres_albaran_por_documento(
        self,
        claves: list[tuple[str, int]],
    ) -> dict[tuple[str, int], Fila]:
        """ALBVENTACAMPOSLIBRES. Clave: (numserie, numalbaran). Maximo una fila."""
        filas = self._ejecutar(
            """
            SELECT
                a.NUMSERIE,
                a.NUMALBARAN,
                a.PEDIDOVTEX
            FROM ALBVENTACAMPOSLIBRES a WITH (NOLOCK)
            WHERE a.NUMSERIE IN :serie_0
              AND a.NUMALBARAN IN :serie_1
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1"),
        )
        return self._agrupar_unico(filas, ("numserie", "numalbaran"), claves)

    def campos_libres_factura_por_documento(
        self,
        claves: list[tuple[str, Any]],
    ) -> dict[tuple[str, Any], Fila]:
        """FACTURASVENTACAMPOSLIBRES. Clave: (numserie, numfac)."""
        filas = self._ejecutar(
            """
            SELECT
                f.NUMSERIE,
                f.NUMFACTURA,
                f.TIPOFACT,
                f.TIPO_NC,
                f.NRO_PEDIDO,
                f.CANAL_VENTA
            FROM FACTURASVENTACAMPOSLIBRES f WITH (NOLOCK)
            WHERE f.NUMSERIE IN :serie_0
              AND f.NUMFACTURA IN :serie_1
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1"),
        )
        return self._agrupar_unico(filas, ("numserie", "numfactura"), claves)

    def tipos_doc_por_codigo(self, codigos: list[int]) -> dict[int, Fila]:
        """TIPOSDOC. Clave simple: tipodoc."""
        filas = self._ejecutar(
            """
            SELECT
                td.TIPODOC,
                td.DESCRIPCION
            FROM TIPOSDOC td WITH (NOLOCK)
            WHERE td.TIPODOC IN :codigos
            """,
            {"codigos": list(codigos)},
            expandibles=("codigos",),
        )
        return {fila["tipodoc"]: fila for fila in filas}

    # =====================================================================
    # MAESTROS DE ARTICULO
    # =====================================================================
    def articulos_por_codigo(self, codigos: list[str]) -> dict[str, Fila]:
        """ARTICULOS. Clave simple: codarticulo."""
        filas = self._ejecutar(
            """
            SELECT
                a.CODARTICULO,
                a.DESCRIPCION,
                a.REFPROVEEDOR,
                a.DPTO,
                a.SECCION,
                a.FAMILIA,
                a.SUBFAMILIA,
                a.MARCA,
                a.DESCATALOGADO
            FROM ARTICULOS a WITH (NOLOCK)
            WHERE a.CODARTICULO IN :codigos
            """,
            {"codigos": list(codigos)},
            expandibles=("codigos",),
        )
        return {fila["codarticulo"]: fila for fila in filas}

    def marcas_por_codigo(self, codigos: list[Any]) -> dict[Any, Fila]:
        """MARCA. Clave simple: codmarca."""
        filas = self._ejecutar(
            """
            SELECT
                m.CODMARCA,
                m.DESCRIPCION
            FROM MARCA m WITH (NOLOCK)
            WHERE m.CODMARCA IN :codigos
            """,
            {"codigos": list(codigos)},
            expandibles=("codigos",),
        )
        return {fila["codmarca"]: fila for fila in filas}

    def secciones_por_clave(
        self,
        claves: list[tuple[Any, Any]],
    ) -> dict[tuple[Any, Any], Fila]:
        """SECCIONES. Clave: (dpto, seccion)."""
        filas = self._ejecutar(
            """
            SELECT
                s.NUMDPTO,
                s.NUMSECCION,
                s.DESCRIPCION
            FROM SECCIONES s WITH (NOLOCK)
            WHERE s.NUMDPTO IN :serie_0
              AND s.NUMSECCION IN :serie_1
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1"),
        )
        return self._agrupar_unico(filas, ("numdpto", "numseccion"), claves)

    def familias_por_clave(
        self,
        claves: list[tuple[Any, Any, Any]],
    ) -> dict[tuple[Any, Any, Any], Fila]:
        """FAMILIAS. Clave: (dpto, seccion, familia)."""
        filas = self._ejecutar(
            """
            SELECT
                f.NUMDPTO,
                f.NUMSECCION,
                f.NUMFAMILIA,
                f.DESCRIPCION
            FROM FAMILIAS f WITH (NOLOCK)
            WHERE f.NUMDPTO IN :serie_0
              AND f.NUMSECCION IN :serie_1
              AND f.NUMFAMILIA IN :serie_2
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1", "serie_2"),
        )
        return self._agrupar_unico(
            filas,
            ("numdpto", "numseccion", "numfamilia"),
            claves,
        )

    def subfamilias_por_clave(
        self,
        claves: list[tuple[Any, Any, Any, Any]],
    ) -> dict[tuple[Any, Any, Any, Any], Fila]:
        """SUBFAMILIAS. Clave: (dpto, seccion, familia, subfamilia)."""
        filas = self._ejecutar(
            """
            SELECT
                sf.NUMDPTO,
                sf.NUMSECCION,
                sf.NUMFAMILIA,
                sf.NUMSUBFAMILIA,
                sf.DESCRIPCION
            FROM SUBFAMILIAS sf WITH (NOLOCK)
            WHERE sf.NUMDPTO IN :serie_0
              AND sf.NUMSECCION IN :serie_1
              AND sf.NUMFAMILIA IN :serie_2
              AND sf.NUMSUBFAMILIA IN :serie_3
            """,
            self._params_de_claves(claves),
            expandibles=("serie_0", "serie_1", "serie_2", "serie_3"),
        )
        return self._agrupar_unico(
            filas,
            ("numdpto", "numseccion", "numfamilia", "numsubfamilia"),
            claves,
        )

    # =====================================================================
    # AYUDAS INTERNAS
    # =====================================================================
    def _ejecutar(
        self,
        sql: str,
        params: dict[str, Any],
        *,
        expandibles: tuple[str, ...] = (),
    ) -> list[Fila]:
        """Ejecuta la consulta y devuelve filas como dicts con claves en minuscula.

        `expandibles` son los parametros que reciben una lista y se convierten
        en un `IN (?, ?, ?)` con tantos placeholders como elementos tenga.
        """
        consulta = text(sql)
        if expandibles:
            consulta = consulta.bindparams(
                *[bindparam(nombre, expanding=True) for nombre in expandibles]
            )

        resultado = self.db_icg.execute(consulta, params)
        return [
            {columna.lower(): valor for columna, valor in fila.items()}
            for fila in resultado.mappings()
        ]

    @staticmethod
    def _params_de_claves(claves: list[tuple]) -> dict[str, list]:
        """De [(a1, b1), (a2, b2)] arma {serie_0: [a1, a2], serie_1: [b1, b2]}.

        Un IN por cada posicion de la clave compuesta, sin valores repetidos.
        """
        if not claves:
            return {}

        cantidad = len(claves[0])
        return {
            f"serie_{posicion}": list({clave[posicion] for clave in claves})
            for posicion in range(cantidad)
        }

    @staticmethod
    def _agrupar_lista(
        filas: list[Fila],
        columnas: tuple[str, ...],
        claves_pedidas: list[tuple],
    ) -> dict[tuple, list[Fila]]:
        """Agrupa filas por clave, descartando combinaciones que no se pidieron."""
        permitidas = set(claves_pedidas)
        agrupado: dict[tuple, list[Fila]] = {}
        for fila in filas:
            clave = tuple(fila[columna] for columna in columnas)
            if clave in permitidas:
                agrupado.setdefault(clave, []).append(fila)
        return agrupado

    @staticmethod
    def _agrupar_unico(
        filas: list[Fila],
        columnas: tuple[str, ...],
        claves_pedidas: list[tuple],
    ) -> dict[tuple, Fila]:
        """Igual que _agrupar_lista pero cuando la clave devuelve una sola fila."""
        permitidas = set(claves_pedidas)
        agrupado: dict[tuple, Fila] = {}
        for fila in filas:
            clave = tuple(fila[columna] for columna in columnas)
            if clave in permitidas:
                agrupado.setdefault(clave, fila)
        return agrupado
