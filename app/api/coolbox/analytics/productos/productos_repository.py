from datetime import date

from sqlalchemy import text

from app.api.coolbox.common.product_types import (
    analytics_product_type_filter,
    analytics_product_type_params,
)


class AnalyticsProductosRepository:
    def __init__(self, db):
        self.db = db

    def get_abc(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
        limit: int = 100,
    ):
        filters_sql = self._filters_sql(
            canal=canal,
            tienda=tienda,
            rubro=rubro,
            familia=familia,
        )

        sql = text(f"""
            WITH ventas_producto AS (
                SELECT
                    p.codigo AS producto,
                    p.descripcion,
                    p.marca,
                    p.rubro,
                    p.familia,
                    COALESCE(SUM(f.total), 0) AS venta_total,
                    COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas
                FROM coolbox.fact_ventas f
                INNER JOIN coolbox.dim_producto p
                    ON p.id = f.producto_id
                INNER JOIN coolbox.dim_canal c
                    ON c.id = f.canal_id
                INNER JOIN coolbox.dim_tienda t
                    ON t.id = f.tienda_id
                WHERE f.fecha >= :fecha_inicio
                AND f.fecha < (:fecha_fin + INTERVAL '1 day')
                {filters_sql}
                GROUP BY
                    p.codigo,
                    p.descripcion,
                    p.marca,
                    p.rubro,
                    p.familia
            ),
            total_general AS (
                SELECT COALESCE(SUM(venta_total), 0) AS total
                FROM ventas_producto
            ),
            calculado AS (
                SELECT
                    vp.*,
                    CASE
                        WHEN tg.total = 0 THEN 0
                        ELSE vp.venta_total / tg.total
                    END AS participacion,
                    CASE
                        WHEN tg.total = 0 THEN 0
                        ELSE SUM(vp.venta_total) OVER (
                            ORDER BY vp.venta_total DESC
                        ) / tg.total
                    END AS participacion_acumulada
                FROM ventas_producto vp
                CROSS JOIN total_general tg
            )
            SELECT
                producto,
                descripcion,
                marca,
                rubro,
                familia,
                venta_total,
                unidades_vendidas,
                participacion,
                participacion_acumulada,
                CASE
                    WHEN participacion_acumulada <= 0.80 THEN 'A'
                    WHEN participacion_acumulada <= 0.95 THEN 'B'
                    ELSE 'C'
                END AS clasificacion_abc
            FROM calculado
            ORDER BY venta_total DESC
            LIMIT :limit
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "limit": limit,
                    **self._filters_params(
                        canal=canal,
                        tienda=tienda,
                        rubro=rubro,
                        familia=familia,
                    ),
                },
            )
            .mappings()
            .all()
        )

    def get_top_productos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
        limit: int = 10,
    ):
        filters_sql = self._filters_sql(
            canal=canal,
            tienda=tienda,
            rubro=rubro,
            familia=familia,
        )

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
            {filters_sql}
            GROUP BY
                p.codigo,
                p.descripcion,
                p.marca,
                p.rubro,
                p.familia
            ORDER BY venta_total DESC
            LIMIT :limit
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "limit": limit,
                    **self._filters_params(
                        canal=canal,
                        tienda=tienda,
                        rubro=rubro,
                        familia=familia,
                    ),
                },
            )
            .mappings()
            .all()
        )

    def get_bajo_movimiento(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
        limit: int = 10,
    ):
        filters_sql = self._filters_sql(
            canal=canal,
            tienda=tienda,
            rubro=rubro,
            familia=familia,
        )

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
            {filters_sql}
            GROUP BY
                p.codigo,
                p.descripcion,
                p.marca,
                p.rubro,
                p.familia
            HAVING COALESCE(SUM(f.cantidad), 0) > 0
            ORDER BY unidades_vendidas ASC, venta_total ASC
            LIMIT :limit
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "limit": limit,
                    **self._filters_params(
                        canal=canal,
                        tienda=tienda,
                        rubro=rubro,
                        familia=familia,
                    ),
                },
            )
            .mappings()
            .all()
        )

    def get_por_rubro(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        filters_sql = self._filters_sql(canal=canal, tienda=tienda)

        sql = text(f"""
            SELECT
                COALESCE(p.rubro, 'SIN RUBRO') AS categoria,
                COALESCE(SUM(f.total), 0) AS venta_total,
                COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas,
                COUNT(DISTINCT p.id) AS cantidad_productos
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_producto p
                ON p.id = f.producto_id
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            {filters_sql}
            GROUP BY COALESCE(p.rubro, 'SIN RUBRO')
            ORDER BY venta_total DESC
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    **self._filters_params(canal=canal, tienda=tienda),
                },
            )
            .mappings()
            .all()
        )

    def get_por_familia(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
    ):
        filters_sql = self._filters_sql(canal=canal, tienda=tienda, rubro=rubro)

        sql = text(f"""
            SELECT
                COALESCE(p.familia, 'SIN FAMILIA') AS categoria,
                COALESCE(SUM(f.total), 0) AS venta_total,
                COALESCE(SUM(f.cantidad), 0) AS unidades_vendidas,
                COUNT(DISTINCT p.id) AS cantidad_productos
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_producto p
                ON p.id = f.producto_id
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            WHERE f.fecha >= :fecha_inicio
            AND f.fecha < (:fecha_fin + INTERVAL '1 day')
            {filters_sql}
            GROUP BY COALESCE(p.familia, 'SIN FAMILIA')
            ORDER BY venta_total DESC
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    **self._filters_params(canal=canal, tienda=tienda, rubro=rubro),
                },
            )
            .mappings()
            .all()
        )

    def get_filtros(self):
        canales_sql = text("""
            SELECT DISTINCT
                c.codigo,
                c.nombre
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_canal c
                ON c.id = f.canal_id
            INNER JOIN coolbox.dim_producto p
                ON p.id = f.producto_id
            WHERE c.activo = TRUE
            AND p.tipo = :analytics_product_type
            ORDER BY c.nombre
        """)

        tiendas_sql = text("""
            SELECT DISTINCT
                t.codigo,
                t.nombre
            FROM coolbox.fact_ventas f
            INNER JOIN coolbox.dim_tienda t
                ON t.id = f.tienda_id
            INNER JOIN coolbox.dim_producto p
                ON p.id = f.producto_id
            WHERE t.activo = TRUE
            AND p.tipo = :analytics_product_type
            ORDER BY t.nombre
        """)

        rubros_sql = text("""
            SELECT DISTINCT rubro AS valor
            FROM coolbox.dim_producto p
            WHERE rubro IS NOT NULL
            AND TRIM(rubro) <> ''
            AND p.tipo = :analytics_product_type
            ORDER BY rubro
        """)

        familias_sql = text("""
            SELECT DISTINCT familia AS valor
            FROM coolbox.dim_producto p
            WHERE familia IS NOT NULL
            AND TRIM(familia) <> ''
            AND p.tipo = :analytics_product_type
            ORDER BY familia
        """)

        marcas_sql = text("""
            SELECT DISTINCT marca AS valor
            FROM coolbox.dim_producto p
            WHERE marca IS NOT NULL
            AND TRIM(marca) <> ''
            AND p.tipo = :analytics_product_type
            ORDER BY marca
        """)

        subfamilias_sql = text("""
            SELECT DISTINCT subfamilia AS valor
            FROM coolbox.dim_producto p
            WHERE subfamilia IS NOT NULL
            AND TRIM(subfamilia) <> ''
            AND p.tipo = :analytics_product_type
            ORDER BY subfamilia
        """)

        params = analytics_product_type_params()

        return {
            "canales": self.db.execute(canales_sql, params).mappings().all(),
            "tiendas": self.db.execute(tiendas_sql, params).mappings().all(),
            "rubros": self.db.execute(rubros_sql, params).mappings().all(),
            "familias": self.db.execute(familias_sql, params).mappings().all(),
            "marcas": self.db.execute(marcas_sql, params).mappings().all(),
            "subfamilias": self.db.execute(subfamilias_sql, params).mappings().all(),
        }

    def _filters_sql(
        self,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
    ):
        filters = [
            # El dashboard de productos se enfoca en articulos de tipo PRO.
            analytics_product_type_filter(),
        ]

        if canal:
            filters.append("AND c.codigo = :canal")

        if tienda:
            filters.append("AND t.codigo = :tienda")

        if rubro:
            filters.append("AND p.rubro = :rubro")

        if familia:
            filters.append("AND p.familia = :familia")

        return "\n                ".join(filters)

    def _filters_params(
        self,
        canal: str | None = None,
        tienda: str | None = None,
        rubro: str | None = None,
        familia: str | None = None,
    ):
        params = analytics_product_type_params()

        if canal:
            params["canal"] = canal

        if tienda:
            params["tienda"] = tienda

        if rubro:
            params["rubro"] = rubro

        if familia:
            params["familia"] = familia

        return params
