from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
import polars as pl

from app.services.analytics_silver.duckdb_utils import register_parquet_or_empty
from app.services.data_lake import DataLakePathBuilder, ParquetDataLakeWriter


@dataclass(frozen=True)
class IcgSilverBuildResult:
    dataset_name: str
    business_date: date
    output_path: str
    rows_count: int


class IcgSilverSalesBuilder:
    def __init__(
        self,
        *,
        paths: DataLakePathBuilder | None = None,
        writer: ParquetDataLakeWriter | None = None,
    ):
        self.paths = paths or DataLakePathBuilder.from_settings()
        self.writer = writer or ParquetDataLakeWriter()

    def build_range(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[IcgSilverBuildResult]:
        if end_date < start_date:
            raise ValueError("end_date no puede ser menor que start_date")

        results = []
        current = start_date
        while current <= end_date:
            results.extend(self.build_day(business_date=current))
            current += timedelta(days=1)
        return results

    def build_day(self, *, business_date: date) -> list[IcgSilverBuildResult]:
        with duckdb.connect(database=":memory:") as con:
            self._register_sources(con, business_date)
            productos = con.execute(self._productos_sql()).pl()
            documentos = con.execute(self._documentos_venta_sql()).pl()
            lineas = con.execute(self._documentos_venta_lineas_sql()).pl()

        return [
            self._write_dataset(
                "productos",
                productos,
                business_date=business_date,
            ),
            self._write_dataset(
                "documentos_venta",
                documentos,
                business_date=business_date,
            ),
            self._write_dataset(
                "documentos_venta_lineas",
                lineas,
                business_date=business_date,
            ),
        ]

    def _write_dataset(
        self,
        dataset_name: str,
        frame: pl.DataFrame,
        *,
        business_date: date,
    ) -> IcgSilverBuildResult:
        partition = self.paths.silver_partition(
            source="icg",
            dataset_name=dataset_name,
            business_date=business_date,
        )
        result = self.writer.write_partition(frame, partition, replace=True)
        return IcgSilverBuildResult(
            dataset_name=dataset_name,
            business_date=business_date,
            output_path=result.output_path,
            rows_count=result.rows_count,
        )

    def _bronze_transactional_file(self, table_name: str, business_date: date) -> Path:
        return self.paths.transactional_partition(
            source="icg",
            table_name=table_name,
            business_date=business_date,
        ) / "data.parquet"

    def _bronze_master_file(self, table_name: str) -> Path:
        return self.paths.master_latest(source="icg", table_name=table_name) / "data.parquet"

    def _register_sources(
        self,
        con: duckdb.DuckDBPyConnection,
        business_date: date,
    ) -> None:
        transactional = {
            "albventacab": self._empty_albventacab(),
            "albventalin": self._empty_albventalin(),
            "facturasventa": self._empty_facturasventa(),
            "facturasventacamposlibres": self._empty_facturasventacamposlibres(),
            "albventacamposlibres": self._empty_albventacamposlibres(),
            "tesoreria": self._empty_tesoreria(),
        }
        for table_name, empty_sql in transactional.items():
            register_parquet_or_empty(
                con,
                view_name=table_name,
                path=self._bronze_transactional_file(table_name, business_date),
                empty_select_sql=empty_sql,
            )

        masters = {
            "tiposdoc": self._empty_tiposdoc(),
            "vendedores": self._empty_vendedores(),
            "vista_articulos": self._empty_vista_articulos(),
            "sbo_articulos_costo": self._empty_sbo_articulos_costo(),
            "almacen": self._empty_almacen(),
        }
        for table_name, empty_sql in masters.items():
            register_parquet_or_empty(
                con,
                view_name=table_name,
                path=self._bronze_master_file(table_name),
                empty_select_sql=empty_sql,
            )

        con.execute(
            """
            CREATE OR REPLACE TEMP VIEW venta_linea_base AS
            SELECT *
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY NUMSERIE, NUMALBARAN, N
                        ORDER BY NUMLIN
                    ) AS rn
                FROM albventalin
            )
            WHERE rn = 1
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TEMP VIEW tesoreria_flags AS
            SELECT
                SERIE,
                NUMERO,
                MAX(CASE WHEN CAST(CODFORMAPAGO AS VARCHAR) = '15' THEN 1 ELSE 0 END) AS es_rappi,
                MAX(CASE WHEN CAST(CODFORMAPAGO AS VARCHAR) = '14' THEN ABS(IMPORTE) ELSE NULL END) AS mkw
            FROM tesoreria
            GROUP BY SERIE, NUMERO
            """
        )
        con.execute(self._productos_view_sql())
        con.execute(self._documentos_venta_view_sql())

    @staticmethod
    def _productos_view_sql() -> str:
        return """
        CREATE OR REPLACE TEMP VIEW productos_tmp AS
        SELECT
            va.CODARTICULO AS codarticulo,
            va.REFPROVEEDOR AS referencia,
            va.DESCRIPCION AS descripcion,
            va.MARCA AS marca,
            va.CO_RUBR AS cod_rubro,
            va.RUBRO AS rubro,
            va.CO_FAMI AS cod_familia,
            va.FAMILIA AS familia,
            va.CO_SFAM AS cod_subfamilia,
            va.SUBFAMILIA AS subfamilia,
            va.CODIGOSAP AS codigo_sap,
            va.ESTADOSARTICULOS AS estado_articulo,
            va.TI_ITEM AS tipo_item,
            va.ORIGEN AS origen,
            va.DESCATALOGADO AS descatalogado,
            TRY_CAST(sc.COSTO AS DOUBLE) AS costo_unitario,
            sc.TIPO AS tipo_costo,
            TRUE AS es_producto,
            FALSE AS es_servicio
        FROM vista_articulos va
        LEFT JOIN sbo_articulos_costo sc
          ON TRIM(CAST(sc.CODIGOSAP AS VARCHAR)) = TRIM(CAST(va.CODIGOSAP AS VARCHAR))
        """

    @staticmethod
    def _productos_sql() -> str:
        return "SELECT * FROM productos_tmp"

    @staticmethod
    def _documentos_venta_view_sql() -> str:
        return """
        CREATE OR REPLACE TEMP VIEW documentos_venta_tmp AS
        SELECT
            CAST(c.FECHA AS DATE) AS fecha,
            c.HORA AS hora,
            l.CODALMACEN AS tienda,
            al.NOMBREALMACEN AS nombre_tienda,
            c.TIPODOC AS tipodoc,
            td.DESCRIPCION AS tipo_documento,
            c.NUMSERIE AS numserie,
            c.NUMALBARAN AS numalbaran,
            c.N AS n,
            CONCAT(c.NUMSERIE, '-', LPAD(CAST(c.NUMALBARAN AS VARCHAR), 10, '0')) AS documento,
            CONCAT(c.NUMSERIE, '-', LPAD(CAST(c.NUMFAC AS VARCHAR), 10, '0')) AS documento_factura,
            c.CODCLIENTE AS codcliente,
            c.CODVENDEDOR AS codvendedor,
            v.DNI AS docvendedor,
            UPPER(v.NOMVENDEDOR) AS nomvendedor,
            fcl.TIPOFACT AS tipo_facturacion,
            fcl.TIPO_NC AS tipo_ncr,
            COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX) AS pedido,
            l.ABONODE_NUMSERIE AS documento_origen_serie,
            l.ABONODE_NUMALBARAN AS documento_origen_numero,
            CASE
                WHEN UPPER(TRIM(fcl.CANAL_VENTA)) IN ('CLICK & COLLECT', 'C&C') THEN 'C&C'
                WHEN UPPER(TRIM(fcl.CANAL_VENTA)) IN ('360', 'VENTA 360') THEN '360'
                WHEN UPPER(TRIM(fcl.CANAL_VENTA)) IN ('E-COMMERCE', 'ECOMMERCE') THEN 'E-COMMERCE'
                WHEN tf.es_rappi = 1 THEN 'RAPPI'
                WHEN UPPER(TRIM(fcl.CANAL_VENTA)) = 'PYA' THEN 'PYA'
                WHEN c.TIPODOC IN (17, 18)
                 AND LENGTH(COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX, '')) > 0
                 AND COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX) = CONCAT(l.ABONODE_NUMSERIE, '-', LPAD(CAST(l.ABONODE_NUMALBARAN AS VARCHAR), 10, '0'))
                    THEN '360'
                WHEN c.TIPODOC IN (17, 18)
                 AND LENGTH(COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX, '')) > 0
                 AND COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX) <> CONCAT(l.ABONODE_NUMSERIE, '-', LPAD(CAST(l.ABONODE_NUMALBARAN AS VARCHAR), 10, '0'))
                    THEN 'E-COMMERCE'
                ELSE 'TIENDA'
            END AS canal,
            CASE WHEN c.TIPODOC IN (17, 18) THEN -1 ELSE 1 END AS signo,
            c.TIPODOC IN (17, 18) AS es_ncr,
            c.TIPODOC IN (5, 13, 37, 38) AS es_venta,
            c.TIPODOC IN (5, 13, 17, 18, 37, 38) AS es_documento_comercial,
            CASE
                WHEN UPPER(TRIM(fcl.CANAL_VENTA)) IN ('CLICK & COLLECT', 'C&C', 'E-COMMERCE', 'ECOMMERCE') THEN TRUE
                WHEN c.TIPODOC IN (17, 18)
                 AND LENGTH(COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX, '')) > 0
                 AND COALESCE(fcl.NRO_PEDIDO, acl.PEDIDOVTEX) <> CONCAT(l.ABONODE_NUMSERIE, '-', LPAD(CAST(l.ABONODE_NUMALBARAN AS VARCHAR), 10, '0'))
                    THEN TRUE
                ELSE FALSE
            END AS es_ecommerce,
            c.NUMSERIE LIKE '%M' AS es_venta_movil,
            ROUND(c.TOTALBRUTO * CASE WHEN c.TIPODOC IN (17, 18) THEN -1 ELSE 1 END, 2) AS total_bruto,
            ROUND(c.TOTALIMPUESTOS * CASE WHEN c.TIPODOC IN (17, 18) THEN -1 ELSE 1 END, 2) AS total_impuestos,
            ROUND(c.TOTALNETO * CASE WHEN c.TIPODOC IN (17, 18) THEN -1 ELSE 1 END, 2) AS total_neto,
            COALESCE(tf.mkw, 0) AS mkw
        FROM albventacab c
        INNER JOIN venta_linea_base l
          ON l.NUMSERIE = c.NUMSERIE
         AND l.NUMALBARAN = c.NUMALBARAN
         AND l.N = c.N
        LEFT JOIN facturasventa fv
          ON fv.NUMSERIE = c.NUMSERIE
         AND fv.NUMFACTURA = c.NUMFAC
        LEFT JOIN facturasventacamposlibres fcl
          ON fcl.NUMSERIE = c.NUMSERIE
         AND fcl.NUMFACTURA = c.NUMFAC
        LEFT JOIN albventacamposlibres acl
          ON acl.NUMSERIE = c.NUMSERIE
         AND acl.NUMALBARAN = c.NUMALBARAN
        LEFT JOIN tesoreria_flags tf
          ON tf.SERIE = c.NUMSERIE
         AND tf.NUMERO = c.NUMFAC
        LEFT JOIN tiposdoc td
          ON td.TIPODOC = c.TIPODOC
        LEFT JOIN vendedores v
          ON v.CODVENDEDOR = c.CODVENDEDOR
        LEFT JOIN almacen al
          ON al.CODALMACEN = l.CODALMACEN
        WHERE c.TIPODOC IN (5, 13, 17, 18, 37, 38)
        """

    @staticmethod
    def _documentos_venta_sql() -> str:
        return "SELECT * FROM documentos_venta_tmp"

    @staticmethod
    def _documentos_venta_lineas_sql() -> str:
        return """
        SELECT
            d.fecha,
            d.hora,
            d.tienda,
            d.nombre_tienda,
            d.tipodoc,
            d.tipo_documento,
            d.documento,
            d.documento_factura,
            d.codcliente,
            d.codvendedor,
            d.docvendedor,
            d.nomvendedor,
            d.canal,
            d.tipo_facturacion,
            d.tipo_ncr,
            d.pedido,
            d.signo,
            d.es_ncr,
            d.es_venta,
            d.es_documento_comercial,
            l.NUMLIN AS secuencia,
            l.CODARTICULO AS codarticulo,
            p.referencia,
            p.descripcion,
            p.marca,
            p.cod_rubro,
            p.rubro,
            p.cod_familia,
            p.familia,
            p.cod_subfamilia,
            p.subfamilia,
            p.codigo_sap,
            l.COLOR AS serie,
            ROUND(l.PRECIO, 2) AS precio,
            ROUND(l.PRECIOIVA, 2) AS precio_con_igv,
            l.UNIDADESTOTAL AS unidades,
            l.UNIDADESTOTAL * d.signo AS unidades_netas,
            ROUND(l.TOTAL, 2) AS total,
            ROUND(l.TOTAL * d.signo, 2) AS venta_neta,
            ROUND(l.TOTAL + (l.TOTAL * (l.IVA / 100)), 2) AS total_con_igv,
            ROUND((l.TOTAL + (l.TOTAL * (l.IVA / 100))) * d.signo, 2) AS venta_neta_con_igv,
            ROUND(l.DTO, 2) AS porcentaje_descuento,
            CASE
                WHEN l.DTO > 0 THEN ROUND((l.PRECIO * (l.DTO / 100)) * l.UNIDADESTOTAL, 2)
                ELSE 0
            END AS descuento,
            ROUND(l.TOTAL * (l.IVA / 100), 2) AS impuesto,
            p.costo_unitario,
            ROUND(COALESCE(p.costo_unitario, 0) * ABS(l.UNIDADESTOTAL) * d.signo, 2) AS costo_total,
            ROUND(
                (l.TOTAL * d.signo)
                - (COALESCE(p.costo_unitario, 0) * ABS(l.UNIDADESTOTAL) * d.signo),
                2
            ) AS contribucion,
            (
                ((l.TOTAL * d.signo)
                - (COALESCE(p.costo_unitario, 0) * ABS(l.UNIDADESTOTAL) * d.signo))
                / NULLIF(l.TOTAL * d.signo, 0)
            ) AS margen,
            p.tipo_costo,
            p.es_producto,
            p.es_servicio
        FROM documentos_venta_tmp d
        INNER JOIN albventalin l
          ON l.NUMSERIE = d.numserie
         AND l.NUMALBARAN = d.numalbaran
         AND l.N = d.n
         AND l.UNIDADESTOTAL <> 0
        LEFT JOIN productos_tmp p
          ON p.codarticulo = l.CODARTICULO
        """

    @staticmethod
    def _empty_albventacab() -> str:
        return """
        SELECT
            CAST(NULL AS DATE) FECHA, CAST(NULL AS TIMESTAMP) HORA,
            CAST(NULL AS INTEGER) CODVENDEDOR, CAST(NULL AS VARCHAR) CODCLIENTE,
            CAST(NULL AS INTEGER) TIPODOC, CAST(NULL AS VARCHAR) NUMSERIE,
            CAST(NULL AS INTEGER) NUMALBARAN, CAST(NULL AS VARCHAR) N,
            CAST(NULL AS INTEGER) NUMFAC, CAST(NULL AS DOUBLE) TOTALBRUTO,
            CAST(NULL AS DOUBLE) TOTALIMPUESTOS, CAST(NULL AS DOUBLE) TOTALNETO
        """

    @staticmethod
    def _empty_albventalin() -> str:
        return """
        SELECT
            CAST(NULL AS VARCHAR) NUMSERIE, CAST(NULL AS INTEGER) NUMALBARAN,
            CAST(NULL AS VARCHAR) N, CAST(NULL AS INTEGER) NUMLIN,
            CAST(NULL AS VARCHAR) CODALMACEN, CAST(NULL AS INTEGER) CODARTICULO,
            CAST(NULL AS DOUBLE) UNIDADESTOTAL, CAST(NULL AS DOUBLE) PRECIO,
            CAST(NULL AS DOUBLE) PRECIOIVA, CAST(NULL AS DOUBLE) TOTAL,
            CAST(NULL AS DOUBLE) IVA, CAST(NULL AS DOUBLE) DTO,
            CAST(NULL AS VARCHAR) ABONODE_NUMSERIE,
            CAST(NULL AS INTEGER) ABONODE_NUMALBARAN,
            CAST(NULL AS VARCHAR) COLOR
        """

    @staticmethod
    def _empty_facturasventa() -> str:
        return "SELECT CAST(NULL AS VARCHAR) NUMSERIE, CAST(NULL AS INTEGER) NUMFACTURA"

    @staticmethod
    def _empty_facturasventacamposlibres() -> str:
        return """
        SELECT
            CAST(NULL AS VARCHAR) NUMSERIE, CAST(NULL AS INTEGER) NUMFACTURA,
            CAST(NULL AS VARCHAR) CANAL_VENTA, CAST(NULL AS VARCHAR) TIPOFACT,
            CAST(NULL AS VARCHAR) NRO_PEDIDO, CAST(NULL AS VARCHAR) TIPO_NC
        """

    @staticmethod
    def _empty_albventacamposlibres() -> str:
        return """
        SELECT
            CAST(NULL AS VARCHAR) NUMSERIE, CAST(NULL AS INTEGER) NUMALBARAN,
            CAST(NULL AS VARCHAR) PEDIDOVTEX
        """

    @staticmethod
    def _empty_tesoreria() -> str:
        return """
        SELECT
            CAST(NULL AS VARCHAR) SERIE, CAST(NULL AS INTEGER) NUMERO,
            CAST(NULL AS VARCHAR) CODFORMAPAGO, CAST(NULL AS DOUBLE) IMPORTE
        """

    @staticmethod
    def _empty_tiposdoc() -> str:
        return "SELECT CAST(NULL AS INTEGER) TIPODOC, CAST(NULL AS VARCHAR) DESCRIPCION"

    @staticmethod
    def _empty_vendedores() -> str:
        return """
        SELECT
            CAST(NULL AS INTEGER) CODVENDEDOR, CAST(NULL AS VARCHAR) DNI,
            CAST(NULL AS VARCHAR) NOMVENDEDOR
        """

    @staticmethod
    def _empty_vista_articulos() -> str:
        return """
        SELECT
            CAST(NULL AS INTEGER) CODARTICULO,
            CAST(NULL AS VARCHAR) REFPROVEEDOR,
            CAST(NULL AS VARCHAR) DESCRIPCION,
            CAST(NULL AS VARCHAR) MARCA,
            CAST(NULL AS VARCHAR) CO_RUBR,
            CAST(NULL AS VARCHAR) RUBRO,
            CAST(NULL AS VARCHAR) CO_FAMI,
            CAST(NULL AS VARCHAR) FAMILIA,
            CAST(NULL AS VARCHAR) CO_SFAM,
            CAST(NULL AS VARCHAR) SUBFAMILIA,
            CAST(NULL AS VARCHAR) CODIGOSAP,
            CAST(NULL AS VARCHAR) ESTADOSARTICULOS,
            CAST(NULL AS VARCHAR) TI_ITEM,
            CAST(NULL AS VARCHAR) ORIGEN,
            CAST(NULL AS BOOLEAN) DESCATALOGADO
        """

    @staticmethod
    def _empty_sbo_articulos_costo() -> str:
        return """
        SELECT
            CAST(NULL AS VARCHAR) CODIGOSAP,
            CAST(NULL AS VARCHAR) DESCRIPCION,
            CAST(NULL AS DOUBLE) COSTO,
            CAST(NULL AS VARCHAR) TIPO
        """

    @staticmethod
    def _empty_almacen() -> str:
        return "SELECT CAST(NULL AS VARCHAR) CODALMACEN, CAST(NULL AS VARCHAR) NOMBREALMACEN"
