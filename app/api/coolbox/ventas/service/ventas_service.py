# app/api/coolbox/ventas/ventas_service.py
from datetime import date
import pandas as pd
import numpy as np
from fastapi import HTTPException, status
from app.api.coolbox.ventas.repository.icg_repository import IcgRepository
from app.api.coolbox.ventas.repository.ventas_dest_repository import VentasDestRepository

class VentasService:
    def __init__(self, db_fuente, db_destino):
        self.repo_fuente = IcgRepository(db_fuente)
        self.repo_destino = VentasDestRepository(db_destino)

    def ejecutar_etl_ventas(self, fecha: date):
        # ---- 1. OBTENER TOTALES DE CONTROL DE LA FUENTE ----
        totales_fuente = self.repo_fuente.obtener_totales_control_fuente(fecha)
        if totales_fuente['total_filas'] == 0:
            return {"message": f"No se encontraron ventas para la fecha {fecha} en la fuente."}

        # ---- 2. EXTRAER DATA CRUDA ----
        data_cruda = self.repo_fuente.get_ventas(fecha)
        
        # Convertimos a DataFrame de Pandas para su manipulación analítica
        df = pd.DataFrame(data_cruda)

        # ---- 3. TRANSFORMAR (Tu lógica de negocio en Python) ----
        
        # A) Reemplazo del CASE WHEN de Canales de venta
        condiciones = [
            df['CANAL_VENTA'].isin(['CLICK & COLLECT', 'C&C']),
            df['CANAL_VENTA'].isin(['360', 'VENTA 360']),
            df['CANAL_VENTA'].isin(['E-COMMERCE', 'ECOMMERCE']),
            df['CODFORMAPAGO'] == '15',
            df['CANAL_VENTA'] == 'PYA'
        ]
        opciones = ['C&C', '360', 'E-COMMERCE', 'RAPPI', 'PYA']
        
        # Para las condiciones complejas del CASE WHEN (tipodoc 17, 18, collates y abonos)
        # Replicamos la lógica usando máscaras lógicas de Pandas
        nro_pedido_vtex = df['NRO_PEDIDO'].fillna(df['PEDIDOVTEX'])
        len_pedido = nro_pedido_vtex.astype(str).str.len()
        abono_doc = df['ABONODE_NUMSERIE'] + '-' + df['ABONODE_NUMALBARAN'].astype(str).str.zfill(10)
        
        condicion_360_compleja = (df['TIPODOC'].isin([17, 18])) & (len_pedido > 0) & (nro_pedido_vtex == abono_doc)
        condicion_eco_compleja = (df['TIPODOC'].isin([17, 18])) & (len_pedido > 0) & (nro_pedido_vtex != abono_doc)
        
        condiciones.extend([condicion_360_compleja, condicion_eco_compleja])
        opciones.extend(['360', 'E-COMMERCE'])
        
        # Aplicamos las condiciones; si ninguna se cumple, por defecto es 'TIENDA' (El ELSE)
        df['CANAL'] = np.select(condiciones, opciones, default='TIENDA')

        # B) Construcción del campo DOCUMENTO
        df['DOCUMENTO'] = df['NUMSERIE'] + '-' + df['NUMALBARAN'].astype(str).str.zfill(10)
        df['MONTO_DESCUENTO'] = (df['UNIDADESTOTAL'] * df['PRECIO']) * (df['DTO'].fillna(0) / 100.0)
        
        # C) Reemplazo del GROUP BY de SQL Server
        # Agrupamos sumando las unidades y totales, y manteniendo fijos los datos descriptivos
        df_agrupado = df.groupby([
            'FECHACREACION', 'FECHA', 'CODCLIENTE', 'DOCUMENTO', 'TIPODOC',
            'CODALMACEN', 'CODARTICULO', 'PRECIO', 'IVA', 'TIPOFACT', 'CANAL'
        ], as_index=False).agg({
            'UNIDADESTOTAL': 'sum',
            'MONTO_DESCUENTO': 'sum',
            'TOTAL': 'sum'
        })

        # ---- 4. GUARDADO IDEMPOTENTE (DELETE-INSERT) ----
        # Limpiamos si existía un procesamiento previo de este día
        self.repo_destino.eliminar_ventas_por_fecha(fecha)
        
        # Insertamos la nueva estructura limpia en Postgres
        self.repo_destino.guardar_ventas_bulk(df_agrupado)

        # ---- 5. VALIDACIÓN CRUZADA (Data Quality Check) ----
        totales_destino = self.repo_destino.obtener_totales_control_destino(fecha)
        
        # Tolerancia para variaciones decimales mínimas por redondeos (ej. 0.05 centavos)
        diferencia_dinero = abs(float(totales_fuente['suma_total']) - float(totales_destino['suma_total']))
        
        if diferencia_dinero > 0.10: # Si la diferencia es mayor a 10 centavos, alerta.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de Calidad de Datos. Fuente suma: {totales_fuente['suma_total']}, Destino suma: {totales_destino['suma_total']}"
            )

        return {
            "status": "Exitoso",
            "fecha_procesada": fecha,
            "filas_origen_procesadas": int(totales_fuente['total_filas']),
            "filas_destino_guardadas": int(totales_destino['total_filas']),
            "monto_validado": float(totales_destino['suma_total'])
        } 