from datetime import date

from sqlalchemy import text


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
    ):
        sql = text("""
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
                AND (:canal IS NULL OR c.codigo = :canal)
                AND (:tienda IS NULL OR t.codigo = :tienda)
                AND (:rubro IS NULL OR p.rubro = :rubro)
                AND (:familia IS NULL OR p.familia = :familia)
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
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "canal": canal,
                    "tienda": tienda,
                    "rubro": rubro,
                    "familia": familia,
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
        sql = text("""
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
            AND (:tienda IS NULL OR t.codigo = :tienda)
            AND (:rubro IS NULL OR p.rubro = :rubro)
            AND (:familia IS NULL OR p.familia = :familia)
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
                    "canal": canal,
                    "tienda": tienda,
                    "rubro": rubro,
                    "familia": familia,
                    "limit": limit,
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
        sql = text("""
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
            AND (:tienda IS NULL OR t.codigo = :tienda)
            AND (:rubro IS NULL OR p.rubro = :rubro)
            AND (:familia IS NULL OR p.familia = :familia)
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
                    "canal": canal,
                    "tienda": tienda,
                    "rubro": rubro,
                    "familia": familia,
                    "limit": limit,
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
        sql = text("""
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
            AND (:canal IS NULL OR c.codigo = :canal)
            AND (:tienda IS NULL OR t.codigo = :tienda)
            GROUP BY COALESCE(p.rubro, 'SIN RUBRO')
            ORDER BY venta_total DESC
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "canal": canal,
                    "tienda": tienda,
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
        sql = text("""
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
            AND (:canal IS NULL OR c.codigo = :canal)
            AND (:tienda IS NULL OR t.codigo = :tienda)
            AND (:rubro IS NULL OR p.rubro = :rubro)
            GROUP BY COALESCE(p.familia, 'SIN FAMILIA')
            ORDER BY venta_total DESC
        """)

        return (
            self.db.execute(
                sql,
                {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "canal": canal,
                    "tienda": tienda,
                    "rubro": rubro,
                },
            )
            .mappings()
            .all()
        )
    def get_filtros(self):
        rubros_sql = text("""
            SELECT DISTINCT rubro AS valor
            FROM coolbox.dim_producto
            WHERE rubro IS NOT NULL
            AND TRIM(rubro) <> ''
            ORDER BY rubro
        """)

        familias_sql = text("""
            SELECT DISTINCT familia AS valor
            FROM coolbox.dim_producto
            WHERE familia IS NOT NULL
            AND TRIM(familia) <> ''
            ORDER BY familia
        """)

        marcas_sql = text("""
            SELECT DISTINCT marca AS valor
            FROM coolbox.dim_producto
            WHERE marca IS NOT NULL
            AND TRIM(marca) <> ''
            ORDER BY marca
        """)

        subfamilias_sql = text("""
            SELECT DISTINCT subfamilia AS valor
            FROM coolbox.dim_producto
            WHERE subfamilia IS NOT NULL
            AND TRIM(subfamilia) <> ''
            ORDER BY subfamilia
        """)

        return {
            "rubros": self.db.execute(rubros_sql).mappings().all(),
            "familias": self.db.execute(familias_sql).mappings().all(),
            "marcas": self.db.execute(marcas_sql).mappings().all(),
            "subfamilias": self.db.execute(subfamilias_sql).mappings().all(),
        }