# app/api/coolbox/tiendas/repository/tiendas_dest_repository.py

from uuid import uuid4

import pandas as pd
from sqlalchemy import text

from app.models.coolbox.ventas.coolbox_ventas_model import DimTienda


class TiendasDestRepository:
    def __init__(self, db_destino):
        self.db = db_destino

    def upsert_dim_tiendas(self, df_limpio: pd.DataFrame):
        registros = []

        for row in df_limpio.itertuples(index=False):
            codigo = row.ALMA_STR_CODIGO

            if pd.isna(codigo):
                continue

            registros.append({
                "id": uuid4(),
                "codigo": str(codigo).strip(),
                "nombre": (
                    str(row.ALMA_STR_DESCRIPCION).strip()
                    if pd.notna(row.ALMA_STR_DESCRIPCION)
                    else str(codigo).strip()
                ),
                "categoria": (
                    str(row.ALMA_STR_CATEGORIA).strip()
                    if pd.notna(row.ALMA_STR_CATEGORIA)
                    else None
                ),
                "region": (
                    str(row.ALMA_STR_REGION).strip()
                    if pd.notna(row.ALMA_STR_REGION)
                    else None
                ),
                "formato": (
                    str(row.TIE_STR_FORMATO).strip()
                    if pd.notna(row.TIE_STR_FORMATO)
                    else None
                ),
                "latitud": (
                    float(row.ALMA_DEC_LATITUD)
                    if pd.notna(row.ALMA_DEC_LATITUD)
                    else None
                ),
                "longitud": (
                    float(row.ALMA_DEC_LONGITUD)
                    if pd.notna(row.ALMA_DEC_LONGITUD)
                    else None
                ),
                "metraje": (
                    float(row.ALMA_DEC_METRAJE)
                    if pd.notna(row.ALMA_DEC_METRAJE)
                    else None
                ),
                "ubigeo": (
                    str(row.ALMA_STR_UBIGEO).strip()
                    if pd.notna(row.ALMA_STR_UBIGEO)
                    else None
                ),
                "departamento": (
                    str(row.DEPARTAMENTO).strip()
                    if pd.notna(row.DEPARTAMENTO)
                    else None
                ),
                "provincia": (
                    str(row.PROVINCIA).strip()
                    if pd.notna(row.PROVINCIA)
                    else None
                ),
                "distrito": (
                    str(row.DISTRITO).strip()
                    if pd.notna(row.DISTRITO)
                    else None
                ),
                "activo": True,
            })

        if not registros:
            return

        sql = text("""
            INSERT INTO coolbox.dim_tienda (
                id,
                codigo,
                nombre,
                categoria,
                region,
                formato,
                latitud,
                longitud,
                metraje,
                ubigeo,
                departamento,
                provincia,
                distrito,
                activo
            )
            VALUES (
                :id,
                :codigo,
                :nombre,
                :categoria,
                :region,
                :formato,
                :latitud,
                :longitud,
                :metraje,
                :ubigeo,
                :departamento,
                :provincia,
                :distrito,
                :activo
            )
            ON CONFLICT (codigo)
            DO UPDATE SET
                nombre = EXCLUDED.nombre,
                categoria = EXCLUDED.categoria,
                region = EXCLUDED.region,
                formato = EXCLUDED.formato,
                latitud = EXCLUDED.latitud,
                longitud = EXCLUDED.longitud,
                metraje = EXCLUDED.metraje,
                ubigeo = EXCLUDED.ubigeo,
                departamento = EXCLUDED.departamento,
                provincia = EXCLUDED.provincia,
                distrito = EXCLUDED.distrito,
                activo = TRUE,
                updated_at = NOW()
        """)

        self.db.execute(sql, registros)

    def contar_tiendas_destino(self):
        return self.db.query(DimTienda).count()
