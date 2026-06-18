from datetime import date
from sqlalchemy import text


class AnalyticsVentasRepository:
    def __init__(self, db):
        self.db = db

    def get_kpis(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        sql = text("""
            SELECT
                COALESCE(SUM(v.total), 0) AS venta_total,
                COUNT(DISTINCT v.documento) AS cantidad_documentos,
                COALESCE(SUM(v.cantidad), 0) AS unidades_vendidas,
                COALESCE(SUM(v.descuento), 0) AS descuento_total,
                COUNT(DISTINCT v.cliente) AS clientes_unicos,
                CASE 
                    WHEN COUNT(DISTINCT v.documento) = 0 THEN 0
                    ELSE COALESCE(SUM(v.total), 0) / COUNT(DISTINCT v.documento)
                END AS ticket_promedio
            FROM coolbox.ventas v
            WHERE v.fecha >= :fecha_inicio
            AND v.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR v.canal = :canal)
            AND (:tienda IS NULL OR v.tienda = :tienda)
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "canal": canal,
                "tienda": tienda,
            },
        ).mappings().one()

    def get_evolucion(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
    ):
        sql = text("""
            SELECT
                CAST(v.fecha AS DATE) AS fecha,
                COALESCE(SUM(v.total), 0) AS venta_total,
                COUNT(DISTINCT v.documento) AS cantidad_documentos,
                COALESCE(SUM(v.cantidad), 0) AS unidades_vendidas,
                CASE 
                    WHEN COUNT(DISTINCT v.documento) = 0 THEN 0
                    ELSE COALESCE(SUM(v.total), 0) / COUNT(DISTINCT v.documento)
                END AS ticket_promedio
            FROM coolbox.ventas v
            WHERE v.fecha >= :fecha_inicio
            AND v.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR v.canal = :canal)
            AND (:tienda IS NULL OR v.tienda = :tienda)
            GROUP BY CAST(v.fecha AS DATE)
            ORDER BY fecha
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "canal": canal,
                "tienda": tienda,
            },
        ).mappings().all()

    def get_por_canal(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        tienda: str | None = None,
    ):
        sql = text("""
            WITH base AS (
                SELECT
                    COALESCE(v.canal, 'SIN CANAL') AS canal,
                    COALESCE(SUM(v.total), 0) AS venta_total,
                    COUNT(DISTINCT v.documento) AS cantidad_documentos,
                    COALESCE(SUM(v.cantidad), 0) AS unidades_vendidas
                FROM coolbox.ventas v
                WHERE v.fecha >= :fecha_inicio
                AND v.fecha < (:fecha_fin + INTERVAL '1 day')
                AND (:tienda IS NULL OR v.tienda = :tienda)
                GROUP BY COALESCE(v.canal, 'SIN CANAL')
            ),
            total AS (
                SELECT COALESCE(SUM(venta_total), 0) AS total_general
                FROM base
            )
            SELECT
                b.canal,
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

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "tienda": tienda,
            },
        ).mappings().all()

    def get_por_tienda(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
    ):
        sql = text("""
            SELECT
                COALESCE(v.tienda, 'SIN TIENDA') AS tienda,
                COALESCE(SUM(v.total), 0) AS venta_total,
                COUNT(DISTINCT v.documento) AS cantidad_documentos,
                COALESCE(SUM(v.cantidad), 0) AS unidades_vendidas,
                CASE 
                    WHEN COUNT(DISTINCT v.documento) = 0 THEN 0
                    ELSE COALESCE(SUM(v.total), 0) / COUNT(DISTINCT v.documento)
                END AS ticket_promedio
            FROM coolbox.ventas v
            WHERE v.fecha >= :fecha_inicio
            AND v.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR v.canal = :canal)
            GROUP BY COALESCE(v.tienda, 'SIN TIENDA')
            ORDER BY venta_total DESC
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "canal": canal,
            },
        ).mappings().all()

    def get_top_productos(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        canal: str | None = None,
        tienda: str | None = None,
        limit: int = 10,
    ):
        sql = text("""
            SELECT
                v.producto,
                MAX(p.descripcion) AS descripcion,
                COALESCE(SUM(v.total), 0) AS venta_total,
                COALESCE(SUM(v.cantidad), 0) AS unidades_vendidas,
                COUNT(DISTINCT v.documento) AS cantidad_documentos
            FROM coolbox.ventas v
            LEFT JOIN coolbox.productos p
                ON p.codigo = v.producto
            WHERE v.fecha >= :fecha_inicio
            AND v.fecha < (:fecha_fin + INTERVAL '1 day')
            AND (:canal IS NULL OR v.canal = :canal)
            AND (:tienda IS NULL OR v.tienda = :tienda)
            GROUP BY v.producto
            ORDER BY venta_total DESC
            LIMIT :limit
        """)

        return self.db.execute(
            sql,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "canal": canal,
                "tienda": tienda,
                "limit": limit,
            },
        ).mappings().all()