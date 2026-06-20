from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from fastapi import HTTPException, status

from app.api.coolbox.ETL.repository.icg_repository import IcgRepository
from app.api.coolbox.ETL.repository.ventas_dest_repository import VentasDestRepository


class VentasService:
    def __init__(self, db_fuente, db_destino):
        self.db_destino = db_destino
        self.repo_fuente = IcgRepository(db_icg=db_fuente)
        self.repo_destino = VentasDestRepository(db_destino)

    def transformar_ventas(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["CANAL_VENTA"] = df["CANAL_VENTA"].fillna("")
        df["CODFORMAPAGO"] = df["CODFORMAPAGO"].fillna("").astype(str)

        condiciones = [
            df["CANAL_VENTA"].isin(["CLICK & COLLECT", "C&C"]),
            df["CANAL_VENTA"].isin(["360", "VENTA 360"]),
            df["CANAL_VENTA"].isin(["E-COMMERCE", "ECOMMERCE"]),
            df["CODFORMAPAGO"] == "15",
            df["CANAL_VENTA"] == "PYA",
        ]

        opciones = ["C&C", "360", "E-COMMERCE", "RAPPI", "PYA"]

        nro_pedido_vtex = df["NRO_PEDIDO"].fillna(df["PEDIDOVTEX"]).fillna("")
        len_pedido = nro_pedido_vtex.astype(str).str.len()

        abono_doc = (
            df["ABONODE_NUMSERIE"].fillna("").astype(str)
            + "-"
            + df["ABONODE_NUMALBARAN"].fillna(0).astype(int).astype(str).str.zfill(10)
        )

        condicion_360_compleja = (
            df["TIPODOC"].isin([17, 18])
            & (len_pedido > 0)
            & (nro_pedido_vtex.astype(str) == abono_doc)
        )

        condicion_eco_compleja = (
            df["TIPODOC"].isin([17, 18])
            & (len_pedido > 0)
            & (nro_pedido_vtex.astype(str) != abono_doc)
        )

        condiciones.extend([condicion_360_compleja, condicion_eco_compleja])
        opciones.extend(["360", "E-COMMERCE"])

        df["CANAL"] = np.select(condiciones, opciones, default="TIENDA")

        df["DOCUMENTO"] = (
            df["NUMSERIE"].astype(str)
            + "-"
            + df["NUMALBARAN"].astype(str).str.zfill(10)
        )

        df["MONTO_DESCUENTO"] = (df["UNIDADESTOTAL"] * df["PRECIO"]) * (
            df["DTO"].fillna(0) / 100.0
        )

        df["TIPODOC"] = df["TIPODOC"].apply(
            lambda x: (
                "FACTURA" if x in [5, 38] else ("BOLETA" if x in [13, 37] else "OTRO")
            )
        )

        df_agrupado = df.groupby(
            [
                "FECHA",
                "CODCLIENTE",
                "DOCUMENTO",
                "TIPODOC",
                "CODALMACEN",
                "CODARTICULO",
                "PRECIO",
                "IVA",
                "CANAL",
                "CODVENDEDOR",
            ],
            as_index=False,
        ).agg(
            {
                "UNIDADESTOTAL": "sum",
                "MONTO_DESCUENTO": "sum",
                "TOTAL": "sum",
            }
        )

        return df_agrupado

    def procesar_fecha(self, fecha: date):
        totales_fuente = self.repo_fuente.obtener_totales_control_fuente(fecha)

        if totales_fuente["total_filas"] == 0:
            return {
                "fecha": str(fecha),
                "status": "Sin Datos",
                "detalle": "No hay ventas en la fuente",
            }

        data_cruda = self.repo_fuente.get_ventas(fecha)
        df = pd.DataFrame(data_cruda)

        if df.empty:
            return {
                "fecha": str(fecha),
                "status": "Sin Datos",
                "detalle": "No hay ventas luego de extraer la fuente",
            }

        df_agrupado = self.transformar_ventas(df)

        # 1. CARGAR STAGING Y CONFIRMARLO
        self.repo_destino.eliminar_stg_ventas_por_fecha(fecha)
        self.repo_destino.guardar_stg_ventas_bulk(df_agrupado)

        self.db_destino.commit()

        # 2. VALIDAR FUENTE VS STAGING
        totales_stg = self.repo_destino.obtener_totales_control_stg(fecha)

        diferencia_fuente_stg = abs(
            float(totales_fuente["suma_total"] or 0)
            - float(totales_stg["suma_total"] or 0)
        )

        if diferencia_fuente_stg > 0.10:
            raise ValueError(
                f"Error de calidad FUENTE vs STG. "
                f"Fuente suma: {totales_fuente['suma_total']}, "
                f"STG suma: {totales_stg['suma_total']}. "
                f"STG quedó guardado para revisión."
            )

        # 3. ASEGURAR DIMENSIONES
        self.repo_destino.asegurar_dim_canales_base()
        self.repo_destino.insertar_canales_no_mapeados_desde_stg(fecha)
        self.repo_destino.insertar_clientes_desde_stg(fecha)
        self.repo_destino.insertar_productos_no_mapeados_desde_stg(fecha)

        # 4. VALIDAR DIMENSIONES
        faltantes = self.repo_destino.obtener_registros_stg_sin_dimension(fecha)

        if (
            faltantes["productos_sin_dimension"] > 0
            or faltantes["tiendas_sin_dimension"] > 0
            or faltantes["canales_sin_dimension"] > 0
        ):
            raise ValueError(
                "Existen registros sin dimensión. "
                f"Productos faltantes: {faltantes['productos_sin_dimension']}, "
                f"Tiendas faltantes: {faltantes['tiendas_sin_dimension']}, "
                f"Canales faltantes: {faltantes['canales_sin_dimension']}. "
                f"STG quedó guardado para revisión."
            )

        # 5. CARGAR FACT
        self.repo_destino.eliminar_fact_ventas_por_fecha(fecha)
        self.repo_destino.insertar_fact_ventas_desde_stg(fecha)

        # 6. VALIDAR STG VS FACT
        totales_fact = self.repo_destino.obtener_totales_control_fact(fecha)

        diferencia_stg_fact = abs(
            float(totales_stg["suma_total"] or 0)
            - float(totales_fact["suma_total"] or 0)
        )

        if diferencia_stg_fact > 0.10:
            raise ValueError(
                f"Error de calidad STG vs FACT. "
                f"STG suma: {totales_stg['suma_total']}, "
                f"Fact suma: {totales_fact['suma_total']}. "
                f"STG quedó guardado para revisión."
            )

        diferencia_cantidad_stg_fact = abs(
            float(totales_stg["suma_cantidad"] or 0)
            - float(totales_fact["suma_cantidad"] or 0)
        )

        if diferencia_cantidad_stg_fact > 0:
            raise ValueError(
                f"Error de cantidad STG vs FACT. "
                f"STG cantidad: {totales_stg['suma_cantidad']}, "
                f"Fact cantidad: {totales_fact['suma_cantidad']}. "
                f"STG quedó guardado para revisión."
            )

        return {
            "fecha": str(fecha),
            "status": "Exitoso",
            "filas_origen": int(totales_fuente["total_filas"]),
            "filas_stg": int(totales_stg["total_filas"]),
            "filas_fact": int(totales_fact["total_filas"]),
            "monto": float(totales_fact["suma_total"]),
        }

    def ejecutar_etl_ventas(self, fecha: date):
        try:
            resultado = self.procesar_fecha(fecha)
            self.db_destino.commit()

            return {
                "status": resultado["status"],
                "fecha_procesada": fecha,
                "detalle": resultado,
            }

        except Exception as e:
            self.db_destino.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error procesando ventas {fecha}: {str(e)}",
            )

    def ejecutar_etl_ventas_rango(self, fecha_inicio: date, fecha_fin: date):
        if fecha_inicio > fecha_fin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de inicio no puede ser mayor a la fecha fin.",
            )

        total_dias = (fecha_fin - fecha_inicio).days + 1
        dias_a_procesar = [fecha_inicio + timedelta(days=x) for x in range(total_dias)]

        reporte_procesamiento = []
        dias_exitosos = 0
        dias_fallidos = 0
        dias_sin_datos = 0

        for fecha in dias_a_procesar:
            try:
                resultado = self.procesar_fecha(fecha)
                self.db_destino.commit()

                if resultado["status"] == "Exitoso":
                    dias_exitosos += 1
                elif resultado["status"] == "Sin Datos":
                    dias_sin_datos += 1

                reporte_procesamiento.append(resultado)

            except Exception as e:
                self.db_destino.rollback()
                dias_fallidos += 1

                reporte_procesamiento.append(
                    {
                        "fecha": str(fecha),
                        "status": "Fallido",
                        "error": str(e),
                    }
                )

        return {
            "resumen": {
                "rango_solicitado": f"{fecha_inicio} a {fecha_fin}",
                "total_dias_rango": total_dias,
                "dias_exitosos": dias_exitosos,
                "dias_sin_datos": dias_sin_datos,
                "dias_fallidos": dias_fallidos,
            },
            "detalle": reporte_procesamiento,
        }

    def ejecutar_etl_ventas_automatico(self, dias_reproceso: int = 2):
        fecha_fin = datetime.now(ZoneInfo("America/Lima")).date()

        fecha_inicio = fecha_fin - timedelta(days=dias_reproceso - 1)

        return self.ejecutar_etl_ventas_rango(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
