import pandas as pd
from fastapi import HTTPException, status

from app.api.coolbox.ETL.repository.icg_repository import IcgRepository
from app.api.coolbox.ETL.repository.productos_dest_repository import (
    ProductosDestRepository,
)


class ProductosService:
    def __init__(self, db_fuente, db_destino):
        self.db_destino = db_destino
        self.repo_fuente = IcgRepository(db_icg=db_fuente)
        self.repo_destino = ProductosDestRepository(db_destino)

    def ejecutar_etl_productos(self):
        try:
            data_cruda = self.repo_fuente.get_productos()

            if not data_cruda:
                raise HTTPException(
                    status_code=404,
                    detail="No se encontraron productos en la fuente.",
                )

            total_fuente = len(data_cruda)
            df = pd.DataFrame(data_cruda)

            df["DESCRIPCION"] = df["DESCRIPCION"].fillna("").astype(str).str.strip()

            df["DESCRIPADIC"] = df["DESCRIPADIC"].fillna("").astype(str).str.strip()

            df["DESCRIPCION_LIMPIA"] = (
                df["DESCRIPCION"] + " " + df["DESCRIPADIC"]
            ).str.strip()

            df["IS_DESCATALOGADO"] = df["DESCATALOGADO"].isin(["S", "s", 1, True])

            self.repo_destino.upsert_dim_productos(df)

            total_destino = self.repo_destino.contar_productos_destino()

            self.db_destino.commit()

            return {
                "status": "Catálogo de productos sincronizado exitosamente",
                "total_registros_fuente": total_fuente,
                "total_registros_dim_producto": total_destino,
            }

        except HTTPException:
            self.db_destino.rollback()
            raise

        except Exception as e:
            self.db_destino.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error procesando productos: {str(e)}",
            )
