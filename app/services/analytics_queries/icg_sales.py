from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

from app.services.analytics_silver.duckdb_utils import sql_path
from app.services.data_lake import DataLakePathBuilder


class IcgSalesAnalyticsQuery:
    def __init__(self, *, paths: DataLakePathBuilder | None = None):
        self.paths = paths or DataLakePathBuilder.from_settings()

    def summary(
        self,
        *,
        start_date: date,
        end_date: date,
        channel: str | None = None,
    ) -> dict[str, Any]:
        with self._connect_sales(start_date, end_date) as con:
            where = self._channel_where(channel)
            row = con.execute(
                f"""
                SELECT
                    COALESCE(SUM(total_neto), 0) AS venta_neta,
                    COUNT(DISTINCT documento) AS pedidos,
                    COALESCE(SUM(CASE WHEN es_ncr THEN 1 ELSE 0 END), 0) AS documentos_ncr,
                    COALESCE(SUM(total_bruto), 0) AS venta_bruta,
                    COALESCE(SUM(total_impuestos), 0) AS impuestos,
                    COALESCE(SUM(total_neto), 0) / NULLIF(COUNT(DISTINCT documento), 0) AS ticket_promedio
                FROM documentos_venta
                {where}
                """
            ).fetchone()
            line_row = con.execute(
                f"""
                SELECT
                    COALESCE(SUM(unidades_netas), 0) AS unidades,
                    COUNT(*) AS lineas,
                    COUNT(*)::DOUBLE / NULLIF(COUNT(DISTINCT documento), 0) AS lineas_por_pedido,
                    COALESCE(SUM(costo_total), 0) AS costo_total,
                    COALESCE(SUM(contribucion), 0) AS contribucion,
                    COALESCE(SUM(contribucion), 0) / NULLIF(COALESCE(SUM(venta_neta), 0), 0) AS margen
                FROM documentos_venta_lineas
                {where}
                """
            ).fetchone()

        return {
            "start_date": start_date,
            "end_date": end_date,
            "channel": channel,
            "venta_neta": row[0],
            "pedidos": row[1],
            "documentos_ncr": row[2],
            "venta_bruta": row[3],
            "impuestos": row[4],
            "ticket_promedio": row[5] or 0,
            "unidades": line_row[0],
            "lineas": line_row[1],
            "lineas_por_pedido": line_row[2] or 0,
            "costo_total": line_row[3],
            "contribucion": line_row[4],
            "margen": line_row[5] or 0,
        }

    def by_channel(self, *, start_date: date, end_date: date) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date) as con:
            return self._rows(
                con,
                """
                SELECT
                    canal,
                    COALESCE(SUM(venta_neta), 0) AS venta_neta,
                    COUNT(DISTINCT documento) AS pedidos,
                    COUNT(DISTINCT CASE WHEN es_ncr THEN documento ELSE NULL END) AS documentos_ncr,
                    COALESCE(SUM(venta_neta), 0) / NULLIF(COUNT(DISTINCT documento), 0) AS ticket_promedio,
                    COALESCE(SUM(costo_total), 0) AS costo_total,
                    COALESCE(SUM(contribucion), 0) AS contribucion,
                    COALESCE(SUM(contribucion), 0) / NULLIF(COALESCE(SUM(venta_neta), 0), 0) AS margen
                FROM documentos_venta_lineas
                GROUP BY canal
                ORDER BY venta_neta DESC
                """,
            )

    def by_store(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date) as con:
            return self._rows(
                con,
                """
                SELECT
                    tienda,
                    ANY_VALUE(nombre_tienda) AS nombre_tienda,
                    COALESCE(SUM(venta_neta), 0) AS venta_neta,
                    COUNT(DISTINCT documento) AS pedidos,
                    COALESCE(SUM(venta_neta), 0) / NULLIF(COUNT(DISTINCT documento), 0) AS ticket_promedio,
                    COALESCE(SUM(costo_total), 0) AS costo_total,
                    COALESCE(SUM(contribucion), 0) AS contribucion,
                    COALESCE(SUM(contribucion), 0) / NULLIF(COALESCE(SUM(venta_neta), 0), 0) AS margen
                FROM documentos_venta_lineas
                GROUP BY tienda
                ORDER BY venta_neta DESC
                LIMIT ?
                """,
                [limit],
            )

    def by_seller(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date) as con:
            return self._rows(
                con,
                """
                SELECT
                    codvendedor,
                    ANY_VALUE(docvendedor) AS docvendedor,
                    ANY_VALUE(nomvendedor) AS nomvendedor,
                    COALESCE(SUM(venta_neta), 0) AS venta_neta,
                    COUNT(DISTINCT documento) AS pedidos,
                    COALESCE(SUM(venta_neta), 0) / NULLIF(COUNT(DISTINCT documento), 0) AS ticket_promedio,
                    COALESCE(SUM(costo_total), 0) AS costo_total,
                    COALESCE(SUM(contribucion), 0) AS contribucion,
                    COALESCE(SUM(contribucion), 0) / NULLIF(COALESCE(SUM(venta_neta), 0), 0) AS margen
                FROM documentos_venta_lineas
                GROUP BY codvendedor
                ORDER BY venta_neta DESC
                LIMIT ?
                """,
                [limit],
            )

    def ecommerce_performance(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date) as con:
            return self._rows(
                con,
                """
                SELECT
                    canal,
                    COALESCE(SUM(venta_neta), 0) AS venta_neta,
                    COUNT(DISTINCT documento) AS pedidos,
                    COALESCE(SUM(unidades_netas), 0) AS unidades,
                    COALESCE(SUM(venta_neta), 0) / NULLIF(COUNT(DISTINCT documento), 0) AS ticket_promedio,
                    COALESCE(SUM(costo_total), 0) AS costo_total,
                    COALESCE(SUM(contribucion), 0) AS contribucion,
                    COALESCE(SUM(contribucion), 0) / NULLIF(COALESCE(SUM(venta_neta), 0), 0) AS margen
                FROM documentos_venta_lineas
                WHERE canal IN ('E-COMMERCE', 'C&C', '360', 'RAPPI', 'PYA')
                GROUP BY canal
                ORDER BY venta_neta DESC
                """,
            )

    def product_abc(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date) as con:
            return self._rows(
                con,
                """
                WITH product_sales AS (
                    SELECT
                        codarticulo,
                        ANY_VALUE(referencia) AS referencia,
                        ANY_VALUE(descripcion) AS descripcion,
                        COALESCE(SUM(unidades_netas), 0) AS unidades,
                        COALESCE(SUM(venta_neta), 0) AS venta_neta,
                        COALESCE(SUM(costo_total), 0) AS costo_total,
                        SUM(contribucion) AS contribucion
                    FROM documentos_venta_lineas
                    WHERE es_producto = TRUE
                    GROUP BY codarticulo
                ),
                ranked AS (
                    SELECT
                        *,
                        SUM(venta_neta) OVER () AS venta_total,
                        SUM(venta_neta) OVER (
                            ORDER BY venta_neta DESC
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS venta_acumulada
                    FROM product_sales
                )
                SELECT
                    codarticulo,
                    referencia,
                    descripcion,
                    unidades,
                    venta_neta,
                    costo_total,
                    contribucion,
                    contribucion / NULLIF(venta_neta, 0) AS margen,
                    venta_neta / NULLIF(venta_total, 0) AS participacion,
                    venta_acumulada / NULLIF(venta_total, 0) AS participacion_acumulada,
                    CASE
                        WHEN (venta_acumulada - venta_neta) / NULLIF(venta_total, 0) < 0.80 THEN 'A'
                        WHEN (venta_acumulada - venta_neta) / NULLIF(venta_total, 0) < 0.95 THEN 'B'
                        ELSE 'C'
                    END AS clase_abc
                FROM ranked
                ORDER BY venta_neta DESC
                LIMIT ?
                """,
                [limit],
            )

    def product_low_movement(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date, include_master_products=True) as con:
            return self._rows(
                con,
                """
                WITH sales AS (
                    SELECT
                        codarticulo,
                        ANY_VALUE(marca) AS marca,
                        ANY_VALUE(rubro) AS rubro,
                        ANY_VALUE(familia) AS familia,
                        ANY_VALUE(subfamilia) AS subfamilia,
                        COALESCE(SUM(unidades_netas), 0) AS unidades,
                        COALESCE(SUM(venta_neta), 0) AS venta_neta,
                        COALESCE(SUM(contribucion), 0) AS contribucion,
                        MAX(fecha) AS ultima_venta
                    FROM documentos_venta_lineas
                    WHERE es_producto = TRUE
                    GROUP BY codarticulo
                )
                SELECT
                    a.CODARTICULO AS codarticulo,
                    a.REFPROVEEDOR AS referencia,
                    a.DESCRIPCION AS descripcion,
                    a.MARCA AS marca,
                    a.RUBRO AS rubro,
                    a.FAMILIA AS familia,
                    a.SUBFAMILIA AS subfamilia,
                    a.CODIGOSAP AS codigo_sap,
                    COALESCE(s.unidades, 0) AS unidades,
                    COALESCE(s.venta_neta, 0) AS venta_neta,
                    COALESCE(s.contribucion, 0) AS contribucion,
                    s.ultima_venta
                FROM vista_articulos a
                LEFT JOIN sales s
                  ON s.codarticulo = a.CODARTICULO
                ORDER BY COALESCE(s.venta_neta, 0), COALESCE(s.unidades, 0), a.CODARTICULO
                LIMIT ?
                """,
                [limit],
            )

    def rfm(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connect_sales(start_date, end_date) as con:
            return self._rows(
                con,
                """
                WITH customer_sales AS (
                    SELECT
                        codcliente,
                        MAX(fecha) AS ultima_compra,
                        COUNT(DISTINCT documento) AS frecuencia,
                        COALESCE(SUM(total_neto), 0) AS monto
                    FROM documentos_venta
                    WHERE codcliente IS NOT NULL
                      AND TRIM(CAST(codcliente AS VARCHAR)) <> ''
                      AND es_documento_comercial = TRUE
                    GROUP BY codcliente
                )
                SELECT
                    codcliente,
                    ultima_compra,
                    DATE_DIFF('day', ultima_compra, ?) AS recencia_dias,
                    frecuencia,
                    monto
                FROM customer_sales
                ORDER BY monto DESC, frecuencia DESC, ultima_compra DESC
                LIMIT ?
                """,
                [end_date, limit],
            )

    def _connect_sales(
        self,
        start_date: date,
        end_date: date,
        *,
        include_master_products: bool = False,
    ):
        con = duckdb.connect(database=":memory:")
        self._register_silver_view(
            con,
            view_name="documentos_venta",
            dataset_name="documentos_venta",
            start_date=start_date,
            end_date=end_date,
            empty_select_sql=self._empty_documentos_venta(),
        )
        self._register_silver_view(
            con,
            view_name="documentos_venta_lineas_raw",
            dataset_name="documentos_venta_lineas",
            start_date=start_date,
            end_date=end_date,
            empty_select_sql=self._empty_documentos_venta_lineas(),
        )
        self._normalize_documentos_venta_lineas_view(con)
        if include_master_products:
            self._register_master_products(con)
        return con

    def _register_silver_view(
        self,
        con: duckdb.DuckDBPyConnection,
        *,
        view_name: str,
        dataset_name: str,
        start_date: date,
        end_date: date,
        empty_select_sql: str,
    ) -> None:
        files = self._silver_files(dataset_name, start_date, end_date)
        if files:
            file_list = ", ".join(f"'{sql_path(path)}'" for path in files)
            con.execute(
                f"""
                CREATE OR REPLACE TEMP VIEW {view_name} AS
                SELECT * FROM read_parquet([{file_list}], union_by_name=true)
                """
            )
            return
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW {view_name} AS
            {empty_select_sql}
            WHERE FALSE
            """
        )

    def _normalize_documentos_venta_lineas_view(
        self,
        con: duckdb.DuckDBPyConnection,
    ) -> None:
        columns = {
            row[0].lower()
            for row in con.execute("DESCRIBE documentos_venta_lineas_raw").fetchall()
        }
        defaults = {
            "tienda": "CAST(NULL AS VARCHAR)",
            "nombre_tienda": "CAST(NULL AS VARCHAR)",
            "codvendedor": "CAST(NULL AS INTEGER)",
            "docvendedor": "CAST(NULL AS VARCHAR)",
            "nomvendedor": "CAST(NULL AS VARCHAR)",
            "marca": "CAST(NULL AS VARCHAR)",
            "rubro": "CAST(NULL AS VARCHAR)",
            "familia": "CAST(NULL AS VARCHAR)",
            "subfamilia": "CAST(NULL AS VARCHAR)",
            "costo_total": "CAST(0 AS DOUBLE)",
            "contribucion": "CAST(NULL AS DOUBLE)",
            "margen": "CAST(NULL AS DOUBLE)",
            "es_ncr": "CAST(FALSE AS BOOLEAN)",
        }
        missing_selects = [
            f"{expression} AS {column_name}"
            for column_name, expression in defaults.items()
            if column_name not in columns
        ]
        extra_sql = ""
        if missing_selects:
            extra_sql = ",\n                " + ",\n                ".join(missing_selects)
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW documentos_venta_lineas AS
            SELECT
                *{extra_sql}
            FROM documentos_venta_lineas_raw
            """
        )

    def _register_master_products(self, con: duckdb.DuckDBPyConnection) -> None:
        path = self.paths.master_latest(source="icg", table_name="vista_articulos") / "data.parquet"
        if path.exists():
            con.execute(
                f"""
                CREATE OR REPLACE TEMP VIEW vista_articulos AS
                SELECT * FROM read_parquet('{sql_path(path)}')
                """
            )
            return
        con.execute(
            """
            CREATE OR REPLACE TEMP VIEW vista_articulos AS
            SELECT
                CAST(NULL AS INTEGER) CODARTICULO,
                CAST(NULL AS VARCHAR) REFPROVEEDOR,
                CAST(NULL AS VARCHAR) DESCRIPCION,
                CAST(NULL AS VARCHAR) MARCA,
                CAST(NULL AS VARCHAR) RUBRO,
                CAST(NULL AS VARCHAR) FAMILIA,
                CAST(NULL AS VARCHAR) SUBFAMILIA,
                CAST(NULL AS VARCHAR) CODIGOSAP
            WHERE FALSE
            """
        )

    def _silver_files(
        self,
        dataset_name: str,
        start_date: date,
        end_date: date,
    ) -> list[Path]:
        if end_date < start_date:
            raise ValueError("end_date no puede ser menor que start_date")

        files = []
        current = start_date
        while current <= end_date:
            path = (
                self.paths.silver_partition(
                    source="icg",
                    dataset_name=dataset_name,
                    business_date=current,
                )
                / "data.parquet"
            )
            if path.exists():
                files.append(path)
            current += timedelta(days=1)
        return files

    @staticmethod
    def _channel_where(channel: str | None) -> str:
        if not channel:
            return ""
        normalized = channel.replace("'", "''").upper()
        return f"WHERE UPPER(canal) = '{normalized}'"

    @staticmethod
    def _rows(
        con: duckdb.DuckDBPyConnection,
        sql: str,
        params: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        result = con.execute(sql, params or [])
        columns = [column[0] for column in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    @staticmethod
    def _empty_documentos_venta() -> str:
        return """
        SELECT
            CAST(NULL AS DATE) fecha,
            CAST(NULL AS VARCHAR) canal,
            CAST(NULL AS VARCHAR) tienda,
            CAST(NULL AS VARCHAR) nombre_tienda,
            CAST(NULL AS VARCHAR) documento,
            CAST(NULL AS VARCHAR) codcliente,
            CAST(NULL AS INTEGER) codvendedor,
            CAST(NULL AS VARCHAR) docvendedor,
            CAST(NULL AS VARCHAR) nomvendedor,
            CAST(NULL AS BOOLEAN) es_ncr,
            CAST(NULL AS BOOLEAN) es_venta,
            CAST(NULL AS BOOLEAN) es_documento_comercial,
            CAST(NULL AS DOUBLE) total_bruto,
            CAST(NULL AS DOUBLE) total_impuestos,
            CAST(NULL AS DOUBLE) total_neto
        """

    @staticmethod
    def _empty_documentos_venta_lineas() -> str:
        return """
        SELECT
            CAST(NULL AS DATE) fecha,
            CAST(NULL AS VARCHAR) canal,
            CAST(NULL AS VARCHAR) tienda,
            CAST(NULL AS VARCHAR) nombre_tienda,
            CAST(NULL AS VARCHAR) documento,
            CAST(NULL AS INTEGER) codvendedor,
            CAST(NULL AS VARCHAR) docvendedor,
            CAST(NULL AS VARCHAR) nomvendedor,
            CAST(NULL AS INTEGER) codarticulo,
            CAST(NULL AS VARCHAR) referencia,
            CAST(NULL AS VARCHAR) descripcion,
            CAST(NULL AS VARCHAR) marca,
            CAST(NULL AS VARCHAR) rubro,
            CAST(NULL AS VARCHAR) familia,
            CAST(NULL AS VARCHAR) subfamilia,
            CAST(NULL AS DOUBLE) unidades_netas,
            CAST(NULL AS DOUBLE) venta_neta,
            CAST(NULL AS DOUBLE) costo_total,
            CAST(NULL AS DOUBLE) contribucion,
            CAST(NULL AS DOUBLE) margen,
            CAST(NULL AS BOOLEAN) es_ncr,
            CAST(NULL AS BOOLEAN) es_producto
        """
