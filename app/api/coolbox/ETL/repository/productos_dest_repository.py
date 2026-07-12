from uuid import uuid4

import pandas as pd
from sqlalchemy import text

from app.api.coolbox.common.product_types import normalize_product_type
from app.models.coolbox.ventas.coolbox_ventas_model import DimProducto


class ProductosDestRepository:
    def __init__(self, db_destino):
        self.db = db_destino

    def upsert_dim_productos(self, df_limpio: pd.DataFrame):
        registros = []

        for row in df_limpio.itertuples(index=False):
            registros.append(
                {
                    "id": uuid4(),
                    "codigo": str(row.CODARTICULO),
                    "codigo_comercial": (
                        str(row.REFPROVEEDOR)
                        if pd.notna(row.REFPROVEEDOR)
                        else None
                    ),
                    "descripcion": row.DESCRIPCION_LIMPIA,
                    "marca": row.MARCA if pd.notna(row.MARCA) else "SIN MARCA",
                    "rubro": row.RUBRO if pd.notna(row.RUBRO) else "SIN RUBRO",
                    "familia": (
                        row.FAMILIA if pd.notna(row.FAMILIA) else "SIN FAMILIA"
                    ),
                    "subfamilia": (
                        row.SUBFAMILIA
                        if pd.notna(row.SUBFAMILIA)
                        else "SIN SUBFAMILIA"
                    ),
                    "tipo": normalize_product_type(row.TI_ITEM),
                    "descatalogado": bool(row.IS_DESCATALOGADO),
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
                activo = TRUE,
                updated_at = NOW()
        """)

        self.db.execute(sql, registros)

    def contar_productos_destino(self):
        return self.db.query(DimProducto).count()
