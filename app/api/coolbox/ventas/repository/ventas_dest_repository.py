# app/api/coolbox/ventas/ventas_dest_repository.py
from datetime import date
from uuid import uuid4
import pandas as pd
from sqlalchemy import text
from app.models.coolbox.ventas.coolbox_ventas_model import Ventas

class VentasDestRepository:
    def __init__(self, db_destino):
        self.db = db_destino

    def eliminar_ventas_por_fecha(self, fecha: date):
        """Paso crucial para la idempotencia: Borra si ya existe data de ese día"""
        self.db.query(Ventas).filter(Ventas.fecha == fecha).delete(synchronize_session=False)
        self.db.commit()

    def guardar_ventas_bulk(self, df_limpio: pd.DataFrame):
        """Convierte el DataFrame procesado en registros de SQLAlchemy y los guarda"""
        registros = []
        for _, row in df_limpio.iterrows():
            registros.append(
                Ventas(
                    id=uuid4(), # Generamos un UUID para cada fila limpia
                    fecha=pd.to_datetime(row['FECHA']),
                    documento=row['DOCUMENTO'],
                    tipo_documento=str(row['TIPODOC']),
                    tienda=row['CODALMACEN'],
                    producto=row['CODARTICULO'],
                    cantidad=int(row['UNIDADESTOTAL']),
                    precio=float(row['PRECIO']),
                    descuento=float(row['MONTO_DESCUENTO']),
                    total=float(row['TOTAL']),
                    canal=row['CANAL'],
                    cliente=row['CODCLIENTE'] ,
                    iva=float(row['IVA']) ,
                    vendedor=row['CODVENDEDOR'] 
                )
            )
        
        self.db.bulk_save_objects(registros)
        self.db.commit()

    def obtener_totales_control_destino(self, fecha: date):
        """Consulta Postgres para verificar cuánto se guardó al final"""
        sql = text("""
            SELECT 
                COUNT(*) as total_filas,
                COALESCE(SUM(total), 0) as suma_total
            FROM coolbox.ventas
            WHERE CAST(fecha AS DATE) = :fecha
        """)
        return self.db.execute(sql, {"fecha": fecha}).mappings().one()