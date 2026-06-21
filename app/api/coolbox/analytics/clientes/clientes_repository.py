from datetime import date

from sqlalchemy import text


class AnalyticsClientesRepository:
    def __init__(self, db):
        self.db = db

    def get_rfm(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 100,
    ):
        filters_sql = self._filters_sql(canal=canal, tienda=tienda)

        sql = text(f"""
            WITH base AS (
                SELECT
                    cl.codigo AS cliente,
                    MAX(CAST(f.fecha AS DATE)) AS ultima_compra,
                    (CAST(:fecha_fin AS DATE) - MAX(CAST(f.fecha AS DATE))) AS recencia,
                    COUNT(DISTINCT f.documento) AS frecuencia,
                    COALESCE(SUM(f.total), 0) AS monetario
                FROM coolbox.fact_ventas f
                INNER JOIN coolbox.dim_cliente cl
                    ON cl.id = f.cliente_id
                INNER JOIN coolbox.dim_canal c
                    ON c.id = f.canal_id
                INNER JOIN coolbox.dim_tienda t
                    ON t.id = f.tienda_id
                WHERE f.fecha >= :fecha_inicio
                AND f.fecha < (:fecha_fin + INTERVAL '1 day')
                AND f.cliente_id IS NOT NULL
                {filters_sql}
                GROUP BY cl.codigo
            ),
            scored AS (
                SELECT
                    *,
                    NTILE(5) OVER (ORDER BY recencia DESC) AS score_recencia,
                    NTILE(5) OVER (ORDER BY frecuencia ASC) AS score_frecuencia,
                    NTILE(5) OVER (ORDER BY monetario ASC) AS score_monetario
                FROM base
            )
            SELECT
                cliente,
                ultima_compra,
                recencia,
                frecuencia,
                monetario,
                score_recencia,
                score_frecuencia,
                score_monetario,
                CONCAT(score_recencia, score_frecuencia, score_monetario) AS score_rfm,
                CASE
                    WHEN score_recencia >= 4
                     AND score_frecuencia >= 4
                     AND score_monetario >= 4
                        THEN 'Mejores clientes'

                    WHEN score_recencia >= 4
                     AND score_frecuencia >= 3
                        THEN 'Clientes leales'

                    WHEN score_recencia >= 4
                     AND frecuencia <= 2
                        THEN 'Clientes nuevos'

                    WHEN score_recencia <= 2
                     AND score_frecuencia >= 4
                        THEN 'En riesgo'

                    WHEN score_recencia <= 2
                     AND score_frecuencia <= 2
                        THEN 'Clientes perdidos'

                    ELSE 'Clientes regulares'
                END AS segmento
            FROM scored
            ORDER BY monetario DESC
            LIMIT :limit
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "limit": limit,
                **self._filters_params(canal=canal, tienda=tienda),
            },
        ).mappings().all()

    def get_segmentos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        filters_sql = self._filters_sql(canal=canal, tienda=tienda)

        sql = text(f"""
            WITH rfm AS (
                WITH base AS (
                    SELECT
                        cl.codigo AS cliente,
                       (CAST(:fecha_fin AS DATE) - MAX(CAST(f.fecha AS DATE))) AS recencia,
                        COUNT(DISTINCT f.documento) AS frecuencia,
                        COALESCE(SUM(f.total), 0) AS monetario
                    FROM coolbox.fact_ventas f
                    INNER JOIN coolbox.dim_cliente cl
                        ON cl.id = f.cliente_id
                    INNER JOIN coolbox.dim_canal c
                        ON c.id = f.canal_id
                    INNER JOIN coolbox.dim_tienda t
                        ON t.id = f.tienda_id
                    WHERE f.fecha >= :fecha_inicio
                    AND f.fecha < (:fecha_fin + INTERVAL '1 day')
                    AND f.cliente_id IS NOT NULL
                    {filters_sql}
                    GROUP BY cl.codigo
                ),
                scored AS (
                    SELECT
                        *,
                        NTILE(5) OVER (ORDER BY recencia DESC) AS score_recencia,
                        NTILE(5) OVER (ORDER BY frecuencia ASC) AS score_frecuencia,
                        NTILE(5) OVER (ORDER BY monetario ASC) AS score_monetario
                    FROM base
                )
                SELECT
                    cliente,
                    frecuencia,
                    monetario,
                    CASE
                        WHEN score_recencia >= 4
                         AND score_frecuencia >= 4
                         AND score_monetario >= 4
                            THEN 'Mejores clientes'

                        WHEN score_recencia >= 4
                         AND score_frecuencia >= 3
                            THEN 'Clientes leales'

                        WHEN score_recencia >= 4
                         AND frecuencia <= 2
                            THEN 'Clientes nuevos'

                        WHEN score_recencia <= 2
                         AND score_frecuencia >= 4
                            THEN 'En riesgo'

                        WHEN score_recencia <= 2
                         AND score_frecuencia <= 2
                            THEN 'Clientes perdidos'

                        ELSE 'Clientes regulares'
                    END AS segmento
                FROM scored
            )
            SELECT
                segmento,
                COUNT(*) AS cantidad_clientes,
                COALESCE(SUM(monetario), 0) AS venta_total,
                CASE
                    WHEN COUNT(*) = 0 THEN 0
                    ELSE COALESCE(SUM(monetario), 0) / COUNT(*)
                END AS ticket_promedio
            FROM rfm
            GROUP BY segmento
            ORDER BY venta_total DESC
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                **self._filters_params(canal=canal, tienda=tienda),
            },
        ).mappings().all()

    def get_top_clientes(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        filters_sql = self._filters_sql(canal=canal, tienda=tienda)

        sql = text(f"""
            SELECT
                cl.codigo AS cliente,
                COALESCE(SUM(f.total), 0) AS venta_total,
                COUNT(DISTINCT f.documento) AS cantidad_documentos,
                MAX(CAST(f.fecha AS DATE)) AS ultima_compra
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_cliente cl
                ON cl.id = f.cliente_id
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            AND f.cliente_id IS NOT NULL
            {filters_sql}
            GROUP BY cl.codigo
            ORDER BY venta_total DESC
            LIMIT :limit
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "limit": limit,
                **self._filters_params(canal=canal, tienda=tienda),
            },
        ).mappings().all()

    def _filters_sql(
        self,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        filters = []

        if canal:
            filters.append("AND c.codigo = :canal")

        if tienda:
            filters.append("AND t.codigo = :tienda")

        return "\n                ".join(filters)

    def _filters_params(
        self,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        params = {}

        if canal:
            params["canal"] = canal

        if tienda:
            params["tienda"] = tienda

        return params

    def get_frecuencia_compra(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        filters_sql = self._filters_sql(canal=canal, tienda=tienda)

        sql = text(f"""
            SELECT
                cl.codigo AS cliente,
                COUNT(DISTINCT f.documento) AS cantidad_documentos,
                MIN(CAST(f.fecha AS DATE)) AS primera_compra,
                MAX(CAST(f.fecha AS DATE)) AS ultima_compra,
                CASE
                    WHEN COUNT(DISTINCT f.documento) <= 1 THEN NULL
                    ELSE
                        (
                            MAX(CAST(f.fecha AS DATE))
                            - MIN(CAST(f.fecha AS DATE))
                        )::numeric
                        / (COUNT(DISTINCT f.documento) - 1)
                END AS dias_entre_compras
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_cliente cl
                ON cl.id = f.cliente_id
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            AND f.cliente_id IS NOT NULL
            {filters_sql}
            GROUP BY cl.codigo
            ORDER BY cantidad_documentos DESC
            LIMIT :limit
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "limit": limit,
                **self._filters_params(canal=canal, tienda=tienda),
            },
        ).mappings().all()

    def get_filtros(self):
        canales_sql = text("""
            SELECT DISTINCT
                c.codigo,
                c.nombre
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            WHERE c.activo = TRUE
            ORDER BY c.nombre
        """)

        tiendas_sql = text("""
            SELECT DISTINCT
                t.codigo,
                t.nombre
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE t.activo = TRUE
            ORDER BY t.nombre
        """)

        return {
            "canales": self.db.execute(canales_sql).mappings().all(),
            "tiendas": self.db.execute(tiendas_sql).mappings().all(),
        }
