# app/api/coolbox/productos/productos_service.py
import pandas as pd
from fastapi import HTTPException, status
from app.api.coolbox.ventas.repository.icg_repository import IcgRepository
from app.api.coolbox.ventas.repository.productos_dest_repository import ProductosDestRepository
class ProductosService:
    def __init__(self, db_fuente, db_destino):
        self.repo_fuente = IcgRepository(db_fuente)
        self.repo_destino = ProductosDestRepository(db_destino)

    def ejecutar_etl_productos(self):
        # 1. Extraer Catálogo de la Fuente
        data_cruda = self.repo_fuente.get_productos()
        if not data_cruda:
            raise HTTPException(status_code=404, detail="No se encontraron productos en la fuente.")
        
        total_fuente = len(data_cruda)
        df = pd.DataFrame(data_cruda)

        # 2. Transformar con Pandas
        # Evitamos problemas de NULL en la descripción rellenando vacíos antes de concatenar
        df['DESCRIPCION'] = df['DESCRIPCION'].fillna('').astype(str).str.strip()
        df['DESCRIPADIC'] = df['DESCRIPADIC'].fillna('').astype(str).str.strip()
        
        df['DESCRIPCION_LIMPIA'] = df['DESCRIPCION'] + ' ' + df['DESCRIPADIC']
        df['DESCRIPCION_LIMPIA'] = df['DESCRIPCION_LIMPIA'].str.strip()

        # Transformar DESCATALOGADO a Boolean real de Python
        # Asumiendo que viene como 'S'/'N' o 1/0 en SQL Server
        df['IS_DESCATALOGADO'] = df['DESCATALOGADO'].isin(['S', 's', 1, True])

        # 3. Carga limpia (Idempotente)
        self.repo_destino.vaciar_productos()
        self.repo_destino.guardar_productos_bulk(df)

        # 4. Validación de Control (Data Quality Check)
        total_destino = self.repo_destino.contar_productos_destino()
        
        if total_fuente != total_destino:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de integridad: Fuente extrajo {total_fuente} productos, pero destino guardó {total_destino}."
            )

        return {
            "status": "Catálogo de productos actualizado exitosamente",
            "total_registros_procesados": total_destino
        }