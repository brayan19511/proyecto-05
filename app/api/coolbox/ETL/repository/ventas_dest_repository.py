# app/api/coolbox/ventas/repository/ventas_dest_repository.py

from datetime import date
from uuid import uuid4

import pandas as pd
from sqlalchemy import text

from app.models.coolbox.ventas.coolbox_ventas_model import (
    StgVenta,
    DimProducto,
    DimTienda,
    DimCanal,
    DimCliente,
    FactVenta,
)


class VentasDestRepository:
    def __init__(self, db_destino):
        self.db = db_destino

    # ============================================================
    # STAGING
    # ============================================================

    def eliminar_stg_ventas_por_fecha(self, fecha: date):
        sql = text("""
            DELETE FROM coolbox.stg_ventas
            WHERE fecha >= :fecha
            AND fecha < (:fecha + INTERVAL '1 day')
        """)

        self.db.execute(sql, {"fecha": fecha})

    def guardar_stg_ventas_bulk(self, df_limpio: pd.DataFrame):
        registros = []

        for row in df_limpio.to_dict("records"):
            registros.append(
                {
                    "id": uuid4(),
                    "fecha": pd.to_datetime(row["FECHA"]),
                    "documento": row["DOCUMENTO"],
                    "tipo_documento": row["TIPODOC"],
                    "tienda_codigo": str(row["CODALMACEN"]),
                    "producto_codigo": str(row["CODARTICULO"]),
                    "canal_codigo": str(row["CANAL"]),
                    "cliente_codigo": (
                        str(row["CODCLIENTE"]) if pd.notna(row["CODCLIENTE"]) else None
                    ),
                    "vendedor_codigo": (
                        str(row["CODVENDEDOR"])
                        if pd.notna(row["CODVENDEDOR"])
                        else None
                    ),
                    "cantidad": int(row["UNIDADESTOTAL"]),
                    "precio": float(row["PRECIO"]),
                    "descuento": float(row["MONTO_DESCUENTO"]),
                    "total": float(row["TOTAL"]),
                    "iva": (float(row["IVA"]) if pd.notna(row["IVA"]) else None),
                }
            )

        if registros:
            self.db.bulk_insert_mappings(StgVenta, registros)

    # ============================================================
    # DIM PRODUCTO
    # ============================================================

    def upsert_dim_productos(self, df_productos: pd.DataFrame):
        registros = []

        for row in df_productos.to_dict("records"):
            registros.append(
                {
                    "id": uuid4(),
                    "codigo": str(row["CODARTICULO"]),
                    "codigo_comercial": (
                        str(row["REFPROVEEDOR"])
                        if pd.notna(row["REFPROVEEDOR"])
                        else None
                    ),
                    "descripcion": row["DESCRIPCION_LIMPIA"],
                    "marca": (row["MARCA"] if pd.notna(row["MARCA"]) else "SIN MARCA"),
                    "rubro": (row["RUBRO"] if pd.notna(row["RUBRO"]) else "SIN RUBRO"),
                    "familia": (
                        row["FAMILIA"] if pd.notna(row["FAMILIA"]) else "SIN FAMILIA"
                    ),
                    "subfamilia": (
                        row["SUBFAMILIA"]
                        if pd.notna(row["SUBFAMILIA"])
                        else "SIN SUBFAMILIA"
                    ),
                    "tipo": (row["TI_ITEM"] if pd.notna(row["TI_ITEM"]) else "OTROS"),
                    "descatalogado": bool(row["IS_DESCATALOGADO"]),
                    "activo": True,
                }
            )

        if not registros:
            return

        sql = text("""
            INSERT INTO coolbox.dim_producto (
                id,
                codigo,
                codigo_comercial,
                descripcion,
                marca,
                rubro,
                familia,
                subfamilia,
                tipo,
                descatalogado,
                activo
            )
            VALUES (
                :id,
                :codigo,
                :codigo_comercial,
                :descripcion,
                :marca,
                :rubro,
                :familia,
                :subfamilia,
                :tipo,
                :descatalogado,
                :activo
            )
            ON CONFLICT (codigo)
            DO UPDATE SET
                codigo_comercial = EXCLUDED.codigo_comercial,
                descripcion = EXCLUDED.descripcion,
                marca = EXCLUDED.marca,
                rubro = EXCLUDED.rubro,
                familia = EXCLUDED.familia,
                subfamilia = EXCLUDED.subfamilia,
                tipo = EXCLUDED.tipo,
                descatalogado = EXCLUDED.descatalogado,
                activo = EXCLUDED.activo,
                updated_at = NOW()
        """)

        self.db.execute(sql, registros)

    # ============================================================
    # DIM TIENDA
    # ============================================================

    def upsert_dim_tiendas(self, df_tiendas: pd.DataFrame):
        registros = []

        for row in df_tiendas.to_dict("records"):
            codigo = row["ALMA_STR_CODIGO"]

            if pd.isna(codigo):
                continue

            registros.append(
                {
                    "id": uuid4(),
                    "codigo": str(codigo),
                    "nombre": (
                        str(row["ALMA_STR_DESCRIPCION"])
                        if pd.notna(row["ALMA_STR_DESCRIPCION"])
                        else str(codigo)
                    ),
                    "tipo": (
                        str(row["ALMA_STR_CATEGORIA"])
                        if pd.notna(row["ALMA_STR_CATEGORIA"])
                        else None
                    ),
                    "zona": (
                        str(row["ALMA_STR_REGION"])
                        if pd.notna(row["ALMA_STR_REGION"])
                        else None
                    ),
                    "activo": True,
                }
            )

        if not registros:
            return

        sql = text("""
            INSERT INTO coolbox.dim_tienda (
                id,
                codigo,
                nombre,
                tipo,
                zona,
                activo
            )
            VALUES (
                :id,
                :codigo,
                :nombre,
                :tipo,
                :zona,
                :activo
            )
            ON CONFLICT (codigo)
            DO UPDATE SET
                nombre = EXCLUDED.nombre,
                tipo = EXCLUDED.tipo,
                zona = EXCLUDED.zona,
                activo = EXCLUDED.activo,
                updated_at = NOW()
        """)

        self.db.execute(sql, registros)

    # ============================================================
    # DIM CANAL
    # ============================================================

    def asegurar_dim_canales_base(self):
        canales = [
            {
                "id": uuid4(),
                "codigo": "TIENDA",
                "nombre": "Tienda física",
                "activo": True,
            },
            {
                "id": uuid4(),
                "codigo": "RAPPI",
                "nombre": "Rappi",
                "activo": True,
            },
            {
                "id": uuid4(),
                "codigo": "PYA",
                "nombre": "PedidosYa",
                "activo": True,
            },
            {
                "id": uuid4(),
                "codigo": "C&C",
                "nombre": "Click & Collect",
                "activo": True,
            },
            {
                "id": uuid4(),
                "codigo": "360",
                "nombre": "Venta 360",
                "activo": True,
            },
            {
                "id": uuid4(),
                "codigo": "E-COMMERCE",
                "nombre": "E-Commerce",
                "activo": True,
            },
        ]

        sql = text("""
            INSERT INTO coolbox.dim_canal (
                id,
                codigo,
                nombre,
                activo
            )
            VALUES (
                :id,
                :codigo,
                :nombre,
                :activo
            )
            ON CONFLICT (codigo)
            DO UPDATE SET
                nombre = EXCLUDED.nombre,
                activo = EXCLUDED.activo,
                updated_at = NOW()
        """)

        self.db.execute(sql, canales)

    def insertar_canales_no_mapeados_desde_stg(self, fecha: date):
        sql = text("""
            INSERT INTO coolbox.dim_canal (
                id,
                codigo,
                nombre,
                activo
            )
            SELECT
                gen_random_uuid(),
                s.canal_codigo,
                s.canal_codigo,
                TRUE
            FROM (
                SELECT DISTINCT canal_codigo
                FROM coolbox.stg_ventas
                WHERE fecha >= :fecha
                AND fecha < (:fecha + INTERVAL '1 day')
                AND canal_codigo IS NOT NULL
            ) s
            LEFT JOIN coolbox.dim_canal c
                ON c.codigo = s.canal_codigo
            WHERE c.id IS NULL
        """)

        self.db.execute(sql, {"fecha": fecha})

    # ============================================================
    # DIM CLIENTE
    # ============================================================

    def insertar_clientes_desde_stg(self, fecha: date):
        sql = text("""
            INSERT INTO coolbox.dim_cliente (
                id,
                codigo,
                activo
            )
            SELECT
                gen_random_uuid(),
                s.cliente_codigo,
                TRUE
            FROM (
                SELECT DISTINCT cliente_codigo
                FROM coolbox.stg_ventas
                WHERE fecha >= :fecha
                AND fecha < (:fecha + INTERVAL '1 day')
                AND cliente_codigo IS NOT NULL
                AND TRIM(cliente_codigo) <> ''
            ) s
            LEFT JOIN coolbox.dim_cliente c
                ON c.codigo = s.cliente_codigo
            WHERE c.id IS NULL
        """)

        self.db.execute(sql, {"fecha": fecha})

    # ============================================================
    # FACT VENTAS
    # ============================================================

    def eliminar_fact_ventas_por_fecha(self, fecha: date):
        sql = text("""
            DELETE FROM coolbox.fact_ventas
            WHERE fecha >= :fecha
            AND fecha < (:fecha + INTERVAL '1 day')
        """)

        self.db.execute(sql, {"fecha": fecha})

    def insertar_fact_ventas_desde_stg(self, fecha: date):
        sql = text("""
            INSERT INTO coolbox.fact_ventas (
                id,
                fecha,
                documento,
                tipo_documento,
                producto_id,
                tienda_id,
                canal_id,
                cliente_id,
                cantidad,
                precio,
                descuento,
                total,
                iva,
                vendedor_codigo
            )
            SELECT
                gen_random_uuid(),
                s.fecha,
                s.documento,
                s.tipo_documento,
                p.id AS producto_id,
                t.id AS tienda_id,
                c.id AS canal_id,
                cl.id AS cliente_id,
                s.cantidad,
                s.precio,
                s.descuento,
                s.total,
                s.iva,
                s.vendedor_codigo
            FROM coolbox.stg_ventas s
            INNER JOIN coolbox.dim_producto p
                ON p.codigo = s.producto_codigo
            INNER JOIN coolbox.dim_tienda t
                ON t.codigo = s.tienda_codigo
            INNER JOIN coolbox.dim_canal c
                ON c.codigo = s.canal_codigo
            LEFT JOIN coolbox.dim_cliente cl
                ON cl.codigo = s.cliente_codigo
            WHERE s.fecha >= :fecha
            AND s.fecha < (:fecha + INTERVAL '1 day')
        """)

        self.db.execute(sql, {"fecha": fecha})

    # ============================================================
    # CONTROLES
    # ============================================================

    def obtener_totales_control_stg(self, fecha: date):
        sql = text("""
            SELECT
                COUNT(*) AS total_filas,
                COALESCE(SUM(total), 0) AS suma_total,
                COALESCE(SUM(cantidad), 0) AS suma_cantidad
            FROM coolbox.stg_ventas
            WHERE fecha >= :fecha
            AND fecha < (:fecha + INTERVAL '1 day')
        """)

        return self.db.execute(sql, {"fecha": fecha}).mappings().one()

    def obtener_totales_control_fact(self, fecha: date):
        sql = text("""
            SELECT
                COUNT(*) AS total_filas,
                COALESCE(SUM(total), 0) AS suma_total,
                COALESCE(SUM(cantidad), 0) AS suma_cantidad
            FROM coolbox.fact_ventas
            WHERE fecha >= :fecha
            AND fecha < (:fecha + INTERVAL '1 day')
        """)

        return self.db.execute(sql, {"fecha": fecha}).mappings().one()

    def obtener_registros_stg_sin_dimension(self, fecha: date):
        sql = text("""
            SELECT
                COUNT(*) FILTER (WHERE p.id IS NULL) AS productos_sin_dimension,
                COUNT(*) FILTER (WHERE t.id IS NULL) AS tiendas_sin_dimension,
                COUNT(*) FILTER (WHERE c.id IS NULL) AS canales_sin_dimension
            FROM coolbox.stg_ventas s
            LEFT JOIN coolbox.dim_producto p
                ON p.codigo = s.producto_codigo
            LEFT JOIN coolbox.dim_tienda t
                ON t.codigo = s.tienda_codigo
            LEFT JOIN coolbox.dim_canal c
                ON c.codigo = s.canal_codigo
            WHERE s.fecha >= :fecha
            AND s.fecha < (:fecha + INTERVAL '1 day')
        """)

        return self.db.execute(sql, {"fecha": fecha}).mappings().one()
