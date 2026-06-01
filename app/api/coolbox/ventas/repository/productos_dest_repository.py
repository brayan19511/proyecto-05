# app/api/coolbox/productos/productos_dest_repository.py
from uuid import uuid4
import pandas as pd
from app.models.coolbox.ventas.coolbox_ventas_model import  Producto # O donde esté tu Base

class ProductosDestRepository:
    def __init__(self, db_destino):
        self.db = db_destino

    def vaciar_productos(self):
        """Borra todos los productos previos para evitar duplicar códigos (Idempotencia)"""
        self.db.query(Producto).delete()
        self.db.commit()

    def guardar_productos_bulk(self, df_limpio: pd.DataFrame):
        """Inserta todo el catálogo limpio en bloques óptimos"""
        registros = []
        for _, row in df_limpio.iterrows():
            registros.append(
                Producto(
                    id=uuid4(),
                    codigo=str(row['CODARTICULO']),
                    codigo_comercial=str(row['REFPROVEEDOR']) if pd.notna(row['REFPROVEEDOR']) else None,
                    descripcion=row['DESCRIPCION_LIMPIA'],
                    marca=row['MARCA'] if pd.notna(row['MARCA']) else 'SIN MARCA',
                    rubro=row['RUBRO'] if pd.notna(row['RUBRO']) else 'SIN RUBRO',
                    familia=row['FAMILIA'] if pd.notna(row['FAMILIA']) else 'SIN FAMILIA',
                    subfamilia=row['SUBFAMILIA'] if pd.notna(row['SUBFAMILIA']) else 'SIN SUBFAMILIA',
                    tipo=row['TI_ITEM'] if pd.notna(row['TI_ITEM']) else 'OTROS',
                    descatalogado=bool(row['IS_DESCATALOGADO'])
                )
            )
        
        # Guardado masivo eficiente
        self.db.bulk_save_objects(registros)
        self.db.commit()

    def contar_productos_destino(self):
        return self.db.query(Producto).count()