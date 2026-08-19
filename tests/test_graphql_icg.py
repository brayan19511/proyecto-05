"""Pruebas del modulo GraphQL de ICG.

Se usa un repositorio falso en lugar de la base de ICG, asi las pruebas corren
sin conexion. Ademas de verificar el resultado, se cuenta cuantas veces se
llamo a cada metodo: es la forma de demostrar que los DataLoaders agrupan las
consultas y no caemos en el problema N+1.
"""

import asyncio
import unittest
from datetime import date, datetime
from decimal import Decimal

from app.api.graphql import graphql_router, schema
from app.api.graphql.loaders import construir_loaders
from app.api.graphql.permissions import ICG_QUERY_VIEW_PERMISSION
from app.api.graphql.repository import IcgGraphRepository
from app.main import app


class PermisoFalso:
    def __init__(self, code: str):
        self.code = code


class UsuarioFalso:
    """Minimo necesario para app.core.access.has_permission."""

    def __init__(self, *codigos: str):
        self.permissions = [PermisoFalso(codigo) for codigo in codigos]
        self.user_roles_links = []


class RepoFalso:
    """Devuelve dos documentos con dos lineas cada uno, del mismo articulo."""

    def __init__(self):
        self.llamadas: dict[str, int] = {}

    def _contar(self, nombre: str) -> None:
        self.llamadas[nombre] = self.llamadas.get(nombre, 0) + 1

    def documentos(self, **kwargs):
        self._contar("documentos")
        self.filtros = kwargs
        columnas_extra = kwargs.get("columnas_extra") or []

        # Valores tomados de una fila real de ICG: N es un caracter ('B'), la
        # hora es un datetime con la fecha centinela 1899-12-30, y los
        # booleanos son char 'T'/'F'.
        base = {
            "numserie": "A01",
            "n": "B",
            "fecha": date(2026, 8, 1),
            "hora": datetime(1899, 12, 30, 15, 22, 29),
            "tipodoc": 5,
            "facturado": "T",
            "tiquet": "T",
            "esdevolucion": "F",
            "ivaincluido": "T",
            "traspasado": "T",
            "fechatraspaso": datetime(1899, 12, 30, 0, 0, 0),
            "fechacreacion": datetime(2026, 8, 1, 15, 22, 28),
            "codvendedor": 875,
            "totalcoste": Decimal("11.0860905"),
        }
        extras = {columna.lower(): "VALOR-EXTRA" for columna in columnas_extra}

        return [
            {
                **base,
                **extras,
                "numalbaran": 100,
                "numfac": 500,
                "codcliente": 1,
                "totalbruto": 118,
                "totalimpuestos": 18,
                "totalneto": 100,
            },
            {
                **base,
                **extras,
                "numalbaran": 101,
                "numfac": 501,
                "codcliente": 2,
                "totalbruto": 236,
                "totalimpuestos": 36,
                "totalneto": 200,
            },
        ]

    def lineas_por_documento(self, claves, *, columnas_extra=None):
        self._contar("lineas_por_documento")
        self.claves_lineas = list(claves)
        self.columnas_linea = list(columnas_extra or [])
        extras = {columna.lower(): "EXTRA-LINEA" for columna in columnas_extra or []}

        # Valores de una linea real de ICG: COLOR y TALLA traen un punto cuando
        # el articulo no tiene el atributo, ABONODE_* trae -1 cuando la linea no
        # abona a nada, y HORA es un datetime completo (no la fecha centinela).
        return {
            clave: [
                {
                    **extras,
                    "numserie": clave[0],
                    "numalbaran": clave[1],
                    "numlin": 1,
                    "n": "B",
                    "tipo": "V",
                    "hora": datetime(2024, 2, 21, 12, 50, 32),
                    "lineaoculta": "F",
                    "codarticulo": "ART-1",
                    "referencia": "PJT-OQT2112",
                    "descripcion": "DEDALES GAMER JETION",
                    "color": ".",
                    "talla": ".",
                    "unidadestotal": 2,
                    "precio": 50,
                    "precioiva": 59,
                    "dto": 20,
                    "total": 100,
                    "coste": Decimal("1.8705"),
                    "prestamo": "F",
                    "idpromocion": -1,
                    "abonode_numserie": "",
                    "abonode_numalbaran": -1,
                    "abonode_numlin": -1,
                    "fechaentrega": datetime(1899, 12, 30, 0, 0, 0),
                }
            ]
            for clave in claves
        }

    def articulos_por_codigo(self, codigos):
        self._contar("articulos_por_codigo")
        self.codigos_articulos = list(codigos)
        return {
            "ART-1": {
                "codarticulo": "ART-1",
                "descripcion": "ZAPATILLA",
                "refproveedor": "REF-1",
                "dpto": 1,
                "seccion": 2,
                "familia": 3,
                "subfamilia": 4,
                "marca": 9,
                "descatalogado": "F",
            }
        }

    def marcas_por_codigo(self, codigos):
        self._contar("marcas_por_codigo")
        return {9: {"codmarca": 9, "descripcion": "NIKE"}}

    def secciones_por_clave(self, claves):
        self._contar("secciones_por_clave")
        return {(1, 2): {"numdpto": 1, "numseccion": 2, "descripcion": "CALZADO"}}

    def familias_por_clave(self, claves):
        self._contar("familias_por_clave")
        return {
            (1, 2, 3): {
                "numdpto": 1,
                "numseccion": 2,
                "numfamilia": 3,
                "descripcion": "URBANO",
            }
        }

    def subfamilias_por_clave(self, claves):
        self._contar("subfamilias_por_clave")
        return {}

    def tesoreria_por_factura(self, claves):
        self._contar("tesoreria_por_factura")
        return {
            clave: [{"codformapago": "1", "importe": 100}]
            for clave in claves
        }

    def campos_libres_albaran_por_documento(self, claves):
        self._contar("campos_libres_albaran_por_documento")
        return {}

    def campos_libres_factura_por_documento(self, claves):
        self._contar("campos_libres_factura_por_documento")
        return {
            clave: {
                "tipofact": "F",
                "tipo_nc": None,
                "nro_pedido": "PED-1",
                "canal_venta": "TIENDA",
            }
            for clave in claves
        }

    def tipos_doc_por_codigo(self, codigos):
        self._contar("tipos_doc_por_codigo")
        return {5: {"tipodoc": 5, "descripcion": "BOLETA"}}


CONSULTA_COMPLETA = """
query {
  documentosVenta(desde: "2026-08-01", hasta: "2026-08-01", limite: 10) {
    numserie
    numalbaran
    totalNeto
    tipoDoc { descripcion }
    tesoreria { codformapago importe }
    camposLibresFactura { canalVenta }
    lineas {
      codarticulo
      unidades
      articulo {
        descripcion
        marca { descripcion }
        seccion { descripcion }
        familia { descripcion }
      }
    }
  }
}
"""


def ejecutar(consulta: str, *, usuario, repo=None):
    repo = repo or RepoFalso()
    contexto = {
        "usuario": usuario,
        "repo": repo,
        "columnas_linea": [],
    }
    contexto["loaders"] = construir_loaders(repo, contexto)
    resultado = asyncio.run(schema.execute(consulta, context_value=contexto))
    return resultado, repo


class GraphqlIcgTests(unittest.TestCase):
    def test_ruta_graphql_publicada(self):
        rutas = {ruta.path for ruta in app.routes}

        self.assertIn("/api/graphql", rutas)
        self.assertEqual(graphql_router.prefix, "/graphql")

    def test_sin_credenciales_rechaza_la_consulta(self):
        resultado, repo = ejecutar(CONSULTA_COMPLETA, usuario=None)

        self.assertTrue(resultado.errors)
        self.assertIn("No autenticado", resultado.errors[0].message)
        # No se toco la base.
        self.assertEqual(repo.llamadas, {})

    def test_sin_el_permiso_rechaza_la_consulta(self):
        usuario = UsuarioFalso("otro.permiso")

        resultado, repo = ejecutar(CONSULTA_COMPLETA, usuario=usuario)

        self.assertTrue(resultado.errors)
        self.assertIn("No tienes permiso", resultado.errors[0].message)
        self.assertEqual(repo.llamadas, {})

    def test_consulta_completa_devuelve_el_grafo_armado(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)

        resultado, _ = ejecutar(CONSULTA_COMPLETA, usuario=usuario)

        self.assertIsNone(resultado.errors)
        documentos = resultado.data["documentosVenta"]
        self.assertEqual(len(documentos), 2)

        primero = documentos[0]
        self.assertEqual(primero["numserie"], "A01")
        self.assertEqual(primero["totalNeto"], 100.0)
        self.assertEqual(primero["tipoDoc"]["descripcion"], "BOLETA")
        self.assertEqual(primero["tesoreria"][0]["importe"], 100.0)
        self.assertEqual(primero["camposLibresFactura"]["canalVenta"], "TIENDA")

        articulo = primero["lineas"][0]["articulo"]
        self.assertEqual(articulo["descripcion"], "ZAPATILLA")
        self.assertEqual(articulo["marca"]["descripcion"], "NIKE")
        self.assertEqual(articulo["seccion"]["descripcion"], "CALZADO")
        self.assertEqual(articulo["familia"]["descripcion"], "URBANO")

    def test_los_loaders_agrupan_las_consultas(self):
        """Con 2 documentos y 2 lineas, cada tabla se consulta UNA sola vez."""
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)

        _, repo = ejecutar(CONSULTA_COMPLETA, usuario=usuario)

        for metodo in (
            "documentos",
            "lineas_por_documento",
            "articulos_por_codigo",
            "marcas_por_codigo",
            "secciones_por_clave",
            "familias_por_clave",
            "tesoreria_por_factura",
            "tipos_doc_por_codigo",
        ):
            self.assertEqual(repo.llamadas[metodo], 1, metodo)

        # Las dos claves llegaron juntas en el mismo lote.
        self.assertEqual(
            sorted(repo.claves_lineas),
            [("A01", 100), ("A01", 101)],
        )
        # El mismo articulo repetido se pide una sola vez (cache del loader).
        self.assertEqual(repo.codigos_articulos, ["ART-1"])

    def test_relaciones_no_pedidas_no_consultan_la_base(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-08-01", hasta: "2026-08-01") {
            numserie
            totalNeto
          }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertEqual(list(repo.llamadas), ["documentos"])

    def test_limite_tiene_techo_duro(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-08-01", hasta: "2026-08-01", limite: 99999) {
            numserie
          }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertEqual(repo.filtros["limite"], 500)

    def test_rango_de_fechas_muy_amplio_se_rechaza(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-01-01", hasta: "2026-08-01") {
            numserie
          }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertTrue(resultado.errors)
        self.assertIn("31 dias", resultado.errors[0].message)
        self.assertEqual(repo.llamadas, {})

    def test_filtro_de_tipodoc_acepta_varios_valores(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            tipodoc: [5, 13, 17]
          ) { numserie }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertEqual(repo.filtros["tipodoc"], [5, 13, 17])

    def test_filtros_de_tablas_relacionadas_llegan_al_repositorio(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            pedido: "PED-1"
            canalVenta: "E-COMMERCE"
          ) { numserie }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertEqual(repo.filtros["pedido"], "PED-1")
        self.assertEqual(repo.filtros["canal_venta"], "E-COMMERCE")

    def test_centinelas_de_la_linea_se_traducen_a_null(self):
        """En ALBVENTALIN el "sin dato" es -1, punto o 1899-12-30, no NULL."""
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-08-01", hasta: "2026-08-01") {
            lineas {
              n
              tipo
              hora
              color
              talla
              referencia
              descripcion
              dto
              coste
              lineaOculta
              idpromocion
              documentoOrigenSerie
              documentoOrigenNumero
              documentoOrigenLinea
              fechaEntrega
            }
          }
        }
        """

        resultado, _ = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        linea = resultado.data["documentosVenta"][0]["lineas"][0]

        # Valores reales
        self.assertEqual(linea["n"], "B")
        self.assertEqual(linea["tipo"], "V")
        self.assertEqual(linea["hora"], "12:50:32")
        self.assertEqual(linea["referencia"], "PJT-OQT2112")
        self.assertEqual(linea["descripcion"], "DEDALES GAMER JETION")
        self.assertEqual(linea["dto"], 20.0)
        self.assertAlmostEqual(linea["coste"], 1.8705)
        self.assertFalse(linea["lineaOculta"])

        # Centinelas -> null
        self.assertIsNone(linea["color"], "COLOR '.' deberia ser null")
        self.assertIsNone(linea["talla"], "TALLA '.' deberia ser null")
        self.assertIsNone(linea["idpromocion"], "IDPROMOCION -1 deberia ser null")
        self.assertIsNone(linea["documentoOrigenSerie"])
        self.assertIsNone(
            linea["documentoOrigenNumero"],
            "ABONODE_NUMALBARAN -1 deberia ser null",
        )
        self.assertIsNone(linea["documentoOrigenLinea"])
        self.assertIsNone(
            linea["fechaEntrega"],
            "FECHAENTREGA 1899-12-30 deberia ser null",
        )

    def test_columnas_extra_de_linea_llegan_en_su_campos_extra(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            columnasLinea: ["numkg", "CARGO1", "TOTAL", "NUMKG"]
          ) {
            lineas { camposExtra }
          }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        # Normalizadas, sin repetidos, y sin TOTAL (ya tiene campo propio).
        self.assertEqual(repo.columnas_linea, ["NUMKG", "CARGO1"])
        self.assertEqual(
            resultado.data["documentosVenta"][0]["lineas"][0]["camposExtra"],
            {"NUMKG": "EXTRA-LINEA", "CARGO1": "EXTRA-LINEA"},
        )

    def test_columna_de_linea_desconocida_se_rechaza(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            columnasLinea: ["NO_EXISTE"]
          ) { numserie }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertTrue(resultado.errors)
        self.assertIn("ALBVENTALIN", resultado.errors[0].message)
        self.assertEqual(repo.llamadas, {})

    def test_columnas_de_linea_disponibles_se_pueden_listar(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)

        resultado, _ = ejecutar(
            "query { columnasLineaVenta }",
            usuario=usuario,
        )

        self.assertIsNone(resultado.errors)
        columnas = resultado.data["columnasLineaVenta"]
        self.assertIn("NUMKG", columnas)
        self.assertIn("IMPORTEMASCARGOS", columnas)
        # Las que ya tienen campo propio no se ofrecen como extra.
        self.assertNotIn("PRECIO", columnas)
        self.assertNotIn("STOCK", columnas)

    def test_la_descripcion_del_producto_no_requiere_join_con_articulos(self):
        """La linea ya trae REFERENCIA y DESCRIPCION."""
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-08-01", hasta: "2026-08-01") {
            lineas { descripcion referencia }
          }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertNotIn("articulos_por_codigo", repo.llamadas)

    def test_columnas_de_icg_se_convierten_a_tipos_de_graphql(self):
        """N es char, la hora viene con fecha centinela y los bool son T/F."""
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-08-01", hasta: "2026-08-01") {
            n
            hora
            facturado
            esDevolucion
            traspasado
            fechaTraspaso
            fechaCreacion
            totalCoste
          }
        }
        """

        resultado, _ = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        documento = resultado.data["documentosVenta"][0]
        self.assertEqual(documento["n"], "B")
        self.assertEqual(documento["hora"], "15:22:29")
        self.assertTrue(documento["facturado"])
        self.assertFalse(documento["esDevolucion"])
        self.assertTrue(documento["traspasado"])
        # 1899-12-30 es "sin fecha" en ICG, no una fecha real.
        self.assertIsNone(documento["fechaTraspaso"])
        self.assertEqual(documento["fechaCreacion"], "2026-08-01T15:22:28")
        self.assertAlmostEqual(documento["totalCoste"], 11.0860905)

    def test_filtro_por_documentos_por_clave_exacta(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(documentos: [
            {numserie: "001", numalbaran: 1}
            {numserie: "001", numfac: 500}
            {numserie: "002", numalbaran: 7, numfac: 9}
          ]) { numserie }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertEqual(
            repo.filtros["claves"],
            [("001", 1, None), ("001", None, 500), ("002", 7, 9)],
        )
        # Con claves exactas el rango de fechas no hace falta.
        self.assertIsNone(repo.filtros["desde"])

    def test_documento_sin_numalbaran_ni_numfac_se_rechaza(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(documentos: [{numserie: "001"}]) { numserie }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertTrue(resultado.errors)
        self.assertIn("numalbaran", resultado.errors[0].message)
        self.assertEqual(repo.llamadas, {})

    def test_sin_fechas_ni_documentos_se_rechaza(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = "query { documentosVenta { numserie } }"

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertTrue(resultado.errors)
        self.assertIn("desde y hasta", resultado.errors[0].message)
        self.assertEqual(repo.llamadas, {})

    def test_columnas_extra_llegan_en_campos_extra(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            columnas: ["sala", "MESA", "SALA"]
          ) { camposExtra }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        # Normalizadas a mayuscula y sin repetidos.
        self.assertEqual(repo.filtros["columnas_extra"], ["SALA", "MESA"])
        self.assertEqual(
            resultado.data["documentosVenta"][0]["camposExtra"],
            {"SALA": "VALOR-EXTRA", "MESA": "VALOR-EXTRA"},
        )

    def test_columna_desconocida_se_rechaza(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            columnas: ["SALA; DROP TABLE ARTICULOS"]
          ) { numserie }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertTrue(resultado.errors)
        self.assertIn("Columnas desconocidas", resultado.errors[0].message)
        self.assertEqual(repo.llamadas, {})

    def test_columna_con_campo_propio_no_se_duplica_en_extras(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(
            desde: "2026-08-01"
            hasta: "2026-08-01"
            columnas: ["TOTALNETO", "SALA"]
          ) { camposExtra }
        }
        """

        resultado, repo = ejecutar(consulta, usuario=usuario)

        self.assertIsNone(resultado.errors)
        self.assertEqual(repo.filtros["columnas_extra"], ["SALA"])

    def test_columnas_disponibles_se_pueden_listar(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)

        resultado, _ = ejecutar(
            "query { columnasDocumentoVenta }",
            usuario=usuario,
        )

        self.assertIsNone(resultado.errors)
        columnas = resultado.data["columnasDocumentoVenta"]
        self.assertIn("SALA", columnas)
        self.assertIn("PUNTOSACUM", columnas)
        # Las que ya tienen campo propio no se ofrecen como extra.
        self.assertNotIn("TOTALNETO", columnas)

    def test_consulta_demasiado_anidada_se_rechaza(self):
        usuario = UsuarioFalso(ICG_QUERY_VIEW_PERMISSION)
        consulta = """
        query {
          documentosVenta(desde: "2026-08-01", hasta: "2026-08-01") {
            lineas { articulo { familia { dpto seccion familia descripcion } } }
          }
        }
        """

        # Profundidad 6, dentro del limite de 8: debe pasar.
        resultado, _ = ejecutar(consulta, usuario=usuario)
        self.assertIsNone(resultado.errors)


class ResultadoFalso:
    def mappings(self):
        return []


class SesionFalsa:
    """Sesion de SQLAlchemy falsa que solo guarda el SQL y los parametros."""

    def __init__(self):
        self.consultas = []

    def execute(self, consulta, params=None):
        self.consultas.append((str(consulta), params))
        return ResultadoFalso()


class SqlDeFiltrosTests(unittest.TestCase):
    """Verifica el SQL que se arma, sin conexion a ICG."""

    def consultar(self, **filtros):
        sesion = SesionFalsa()
        repo = IcgGraphRepository(sesion)
        repo.documentos(
            desde=date(2026, 8, 1),
            hasta=date(2026, 8, 1),
            **filtros,
        )
        return sesion.consultas[0]

    def test_sin_filtros_solo_filtra_por_fecha(self):
        sql, params = self.consultar()

        self.assertIn("c.FECHA >= :desde", sql)
        self.assertNotIn("EXISTS", sql)
        self.assertNotIn("TIPODOC IN", sql)
        self.assertEqual(sorted(params), ["desde", "hasta", "limite"])

    def test_tipodoc_genera_un_in(self):
        sql, params = self.consultar(tipodoc=[5, 13])

        self.assertIn("c.TIPODOC IN", sql)
        self.assertEqual(params["tipodoc"], [5, 13])

    def test_tipodoc_vacio_no_agrega_condicion(self):
        sql, params = self.consultar(tipodoc=[])

        self.assertNotIn("TIPODOC IN", sql)
        self.assertNotIn("tipodoc", params)

    def test_pedido_busca_en_las_dos_tablas_de_campos_libres(self):
        sql, params = self.consultar(pedido="PED-1")

        self.assertIn("FACTURASVENTACAMPOSLIBRES", sql)
        self.assertIn("NRO_PEDIDO", sql)
        self.assertIn("ALBVENTACAMPOSLIBRES", sql)
        self.assertIn("PEDIDOVTEX", sql)
        self.assertEqual(params["pedido"], "PED-1")

    def test_canal_venta_normaliza_mayusculas_y_espacios(self):
        sql, params = self.consultar(canal_venta="  e-commerce  ")

        self.assertIn("CANAL_VENTA", sql)
        self.assertEqual(params["canal_venta"], "E-COMMERCE")

    def test_tienda_filtra_por_la_linea(self):
        sql, params = self.consultar(tienda="T01")

        self.assertIn("ALBVENTALIN", sql)
        self.assertIn("l.CODALMACEN = :tienda", sql)
        self.assertEqual(params["tienda"], "T01")

    def test_los_filtros_se_combinan_con_and(self):
        sql, params = self.consultar(
            tipodoc=[17, 18],
            tienda="T01",
            pedido="PED-1",
            canal_venta="TIENDA",
        )

        self.assertEqual(sql.count("EXISTS"), 4)
        self.assertEqual(
            sorted(params),
            [
                "canal_venta",
                "desde",
                "hasta",
                "limite",
                "pedido",
                "tienda",
                "tipodoc",
            ],
        )

    def test_claves_de_documento_generan_bloques_con_or(self):
        sesion = SesionFalsa()
        IcgGraphRepository(sesion).documentos(
            claves=[("001", 1, None), ("001", None, 500), ("002", 7, 9)]
        )
        sql, params = sesion.consultas[0]

        self.assertIn(
            "(c.NUMSERIE = :doc0_serie AND c.NUMALBARAN = :doc0_alb)",
            sql,
        )
        self.assertIn(
            "(c.NUMSERIE = :doc1_serie AND c.NUMFAC = :doc1_fac)",
            sql,
        )
        self.assertIn(
            "(c.NUMSERIE = :doc2_serie AND c.NUMALBARAN = :doc2_alb "
            "AND c.NUMFAC = :doc2_fac)",
            sql,
        )
        self.assertEqual(sql.count(" OR "), 2)
        self.assertEqual(params["doc1_fac"], 500)
        # Sin rango de fechas la consulta no filtra por FECHA.
        self.assertNotIn("c.FECHA >=", sql)

    def test_sin_fechas_ni_claves_el_repositorio_falla(self):
        with self.assertRaisesRegex(ValueError, "rango de fechas"):
            IcgGraphRepository(SesionFalsa()).documentos()

    def test_las_columnas_extra_entran_al_select(self):
        sql, _ = self.consultar(columnas_extra=["SALA", "MESA"])

        self.assertIn("c.SALA", sql)
        self.assertIn("c.MESA", sql)
        # El SELECT sigue siendo explicito.
        self.assertNotIn("SELECT *", sql)

    def test_el_select_base_sale_del_catalogo(self):
        from app.api.graphql.columnas import COLUMNAS_BASE

        sql, _ = self.consultar()

        for columna in COLUMNAS_BASE:
            self.assertIn(f"c.{columna}", sql)

    def test_ningun_valor_se_interpola_en_el_sql(self):
        """Los valores siempre viajan como parametros, nunca dentro del texto."""
        sql, _ = self.consultar(
            tienda="T01",
            pedido="'; DROP TABLE ARTICULOS; --",
            canal_venta="TIENDA",
        )

        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("T01", sql)


if __name__ == "__main__":
    unittest.main()
