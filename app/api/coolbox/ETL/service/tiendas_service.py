# app/api/coolbox/tiendas/tiendas_service.py

import pandas as pd
from fastapi import HTTPException, status

from app.api.coolbox.ETL.repository.icg_repository import IcgRepository
from app.api.coolbox.ETL.repository.tiendas_dest_repository import TiendasDestRepository


class TiendasService:
    def __init__(self, db_fuente, db_destino):
        self.db_destino = db_destino
        self.repo_fuente = IcgRepository(db_icg=db_fuente)
        self.repo_destino = TiendasDestRepository(db_destino)

    def ejecutar_etl_tiendas(self):
        try:
            data_cruda = self.repo_fuente.get_tiendas()

            if not data_cruda:
                raise HTTPException(
                    status_code=404,
                    detail="No se encontraron tiendas en la fuente.",
                )

            total_fuente = len(data_cruda)
            df = pd.DataFrame(data_cruda)

            self.repo_destino.upsert_dim_tiendas(df)

            total_destino = self.repo_destino.contar_tiendas_destino()

            self.db_destino.commit()

            return {
                "status": "Tiendas sincronizadas exitosamente",
                "total_registros_fuente": total_fuente,
                "total_registros_dim_tienda": total_destino,
            }

        except HTTPException:
            self.db_destino.rollback()
            raise

        except Exception as e:
            self.db_destino.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error procesando tiendas: {str(e)}",
            )