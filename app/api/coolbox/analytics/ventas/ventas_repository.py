from datetime import date

from sqlalchemy import bindparam, text


class AnalyticsVentasRepository:
    def __init__(self, db):
        self.db = db

    def get_kpis(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
    ):
        tiendas_filter = self._tiendas_filter_sql(tiendas)

        sql = text(f"""
            SELECT
                COALESCE(SUM(f.total), 0) AS venta_total,
                COUNT(DISTINCT f.documento) AS cantidad_documentos,
                COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas,
                COALESCE(SUM(f.descuento), 0) AS descuento_total,
                COUNT(DISTINCT f.cliente_id) AS clientes_unicos,
                CASE
                    WHEN COUNT(DISTINCT f.documento) = 0 THEN 0
                    ELSE COALESCE(SUM(f.total), 0) / COUNT(DISTINCT f.documento)
                END AS ticket_promedio
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR c.codigo = :canal)
            {tiendas_filter}
        """)

        if tiendas:
            sql = sql.bindparams(bindparam("tiendas", expanding=True))

        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "canal": canal,
            **self._tiendas_params(tiendas),
        }

        return self.db.execute(sql, params).mappings().one()

    def get_evolucion(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
    ):
        tiendas_filter = self._tiendas_filter_sql(tiendas)

        sql = text(f"""
            SELECT
                CAST(f.fecha AS DATE) AS fecha,
                COALESCE(SUM(f.total), 0) AS venta_total,
                COUNT(DISTINCT f.documento) AS cantidad_documentos,
                COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas,
                CASE
                    WHEN COUNT(DISTINCT f.documento) = 0 THEN 0
                    ELSE COALESCE(SUM(f.total), 0) / COUNT(DISTINCT f.documento)
                END AS ticket_promedio
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR c.codigo = :canal)
            {tiendas_filter}
            GROUP BY CAST(f.fecha AS DATE)
            ORDER BY fecha
        """)

        if tiendas:
            sql = sql.bindparams(bindparam("tiendas", expanding=True))

        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "canal": canal,
            **self._tiendas_params(tiendas),
        }

        return self.db.execute(sql, params).mappings().all()

    def get_por_canal(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        tiendas: list[str] | None = None,
    ):
        tiendas_filter = self._tiendas_filter_sql(tiendas)

        sql = text(f"""
            WITH base AS (
                SELECT
                    c.codigo AS canal,
                    c.nombre AS canal_nombre,
                    COALESCE(SUM(f.total), 0) AS venta_total,
                    COUNT(DISTINCT f.documento) AS cantidad_documentos,
                    COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas
                FROM coolbox.fact_ventas f
                INNER JOIN coolbox.dim_canal c
                    ON c.id = f.canal_id
                INNER JOIN coolbox.dim_tienda t
                    ON t.id = f.tienda_id
                WHERE f.fecha >= :fecha_inicio
                AND f.fecha < (:fecha_fin + INTERVAL '1 day')
                {tiendas_filter}
                GROUP BY c.codigo, c.nombre
            ),
            total AS (
                SELECT COALESCE(SUM(venta_total), 0) AS total_general
                FROM base
            )
            SELECT
                b.canal,
                b.canal_nombre,
                b.venta_total,
                b.cantidad_documentos,
                b.unidades_vendidas,
                CASE
                    WHEN t.total_general = 0 THEN 0
                    ELSE b.venta_total / t.total_general
                END AS participacion
            FROM base b
            CROSS JOIN total t
            ORDER BY b.venta_total DESC
        """)

        if tiendas:
            sql = sql.bindparams(bindparam("tiendas", expanding=True))

        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            **self._tiendas_params(tiendas),
        }

        return self.db.execute(sql, params).mappings().all()

    def get_por_tienda(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        limit: int | None = 10,
    ):
        sql = text("""
            SELECT
                t.codigo AS tienda,
                t.nombre AS tienda_nombre,
                COALESCE(SUM(f.total), 0) AS venta_total,
                COUNT(DISTINCT f.documento) AS cantidad_documentos,
                COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas,
                CASE
                    WHEN COUNT(DISTINCT f.documento) = 0 THEN 0
                    ELSE COALESCE(SUM(f.total), 0) / COUNT(DISTINCT f.documento)
                END AS ticket_promedio
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR c.codigo = :canal)
            GROUP BY t.codigo, t.nombre
            ORDER BY venta_total DESC
            LIMIT :limit
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "canal": canal,
                "limit": limit or 10,
            },
        ).mappings().all()

    def get_top_productos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tiendas: list[str] | None = None,
        limit: int = 10,
    ):
        tiendas_filter = self._tiendas_filter_sql(tiendas)

        sql = text(f"""
            SELECT
                p.codigo AS producto,
                p.descripcion,
                p.marca,
                p.rubro,
                p.familia,
                COALESCE(SUM(f.total), 0) AS venta_total,
                COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas,
                COUNT(DISTINCT f.documento) AS cantidad_documentos
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_producto p
                ON p.id = f.producto_id
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR c.codigo = :canal)
            {tiendas_filter}
            GROUP BY
                p.codigo,
                p.descripcion,
                p.marca,
                p.rubro,
                p.familia
            ORDER BY venta_total DESC
            LIMIT :limit
        """)

        if tiendas:
            sql = sql.bindparams(bindparam("tiendas", expanding=True))

        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "canal": canal,
            "limit": limit,
            **self._tiendas_params(tiendas),
        }

        return self.db.execute(sql, params).mappings().all()

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

        canales = self.db.execute(canales_sql).mappings().all()
        tiendas = self.db.execute(tiendas_sql).mappings().all()

        return {
            "canales": canales,
            "tiendas": tiendas,
        }
    def _tiendas_filter_sql(self, tiendas: list[str] | None):
        if tiendas:
            return "AND t.codigo IN :tiendas"

        return ""

    def _tiendas_params(self, tiendas: list[str] | None):
        if tiendas:
            return {"tiendas": tiendas}

        return {}