# app/api/sap/finance/sap_finance_service.py
from datetime import date, datetime
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.api.sap.finance.sap_finance_repository import SapRepository
from app.api.sap.libro_mayor.LibroMayorRepository import LibroMayorRepository
from app.core.audit_utils import add_step
from app.models.finance.libro_mayor_model import LibroMayor


class SapFinanceService:
    def __init__(
        self, db_sap: Session, db_local: Session, company: str = "SBO_RASH_PRODUCCION", user_id: Optional[str] = None
    ):
        self.company = company
        self.sap_repo = SapRepository(db_sap, self.company)
        self.local_repo = LibroMayorRepository(db_local)
        self.user_id = user_id  # Integrado con el ID de usuario real de tu auth

    def _sanitizar_y_diagnosticar(self, registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Inspecciona registro por registro antes de guardarlo en PostgreSQL.
        1. Convierte los NaNs/Floats extraños de Pandas a None nativo.
        2. Valida los rangos e imprime diagnósticos exactos en add_step si algo va a fallar.
        """
        datos_limpios = []
        rango_int32_max = 2147483647
        rango_int32_min = -2147483648

        for idx, reg in enumerate(registros):
            registro_limpio = {}
            doc_info = f"TransId: {reg.get('transaccion_id')}, Linea: {reg.get('linea')}, DocNum: {reg.get('numero_documento')}"

            for columna, valor in reg.items():
                # 1. Limpieza de nulos e infinitos de Pandas/Numpy
                if pd.isna(valor) or (isinstance(valor, float) and np.isinf(valor)):
                    registro_limpio[columna] = None
                
                # 2. Control de enteros y detección de desbordamiento (Integer Out Of Range)
                elif columna in ["transaccion_id", "linea", "id_regla"]:
                    try:
                        val_int = int(float(valor))
                        # Si tu columna en PostgreSQL sigue siendo INT (32 bits), diagnosticamos aquí:
                        # Si ya migraste a BIGINT, puedes omitir o subir este rango.
                        if val_int > rango_int32_max or val_int < rango_int32_min:
                            add_step(
                                name="⚠️ ALERTA: Desborde Numérico Detectado",
                                status="WARNING",
                                message=f"Fila {idx} ({doc_info}) -> Columna '{columna}' tiene el valor {val_int} que supera el límite de un INT estándar."
                            )
                        registro_limpio[columna] = val_int
                    except (ValueError, TypeError):
                        add_step(
                            name="❌ ERROR: Tipo de dato no convertible",
                            status="ERROR",
                            message=f"Fila {idx} ({doc_info}) -> Columna '{columna}' tiene un valor no entero: {valor}"
                        )
                        registro_limpio[columna] = None
                
                # 3. Mantener el resto de valores intactos
                else:
                    registro_limpio[columna] = valor
            
            datos_limpios.append(registro_limpio)
            
        return datos_limpios

    def _ejecutar_motor_de_reglas(self, df_sap: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Toma un DataFrame con datos del Libro Mayor y le aplica las reglas
        configradas en la base de datos local de manera secuencial por prioridad.
        """
        if df_sap.empty:
            return []

        # 1. Obtener reglas activas ordenadas por prioridad
        reglas = self.local_repo.get_reglas_activas()
        add_step(
            name="Reglas de gastos activas obtenidas desde la base local",
            message=f"cantidad: {len(reglas)}",
        )

        # 2. Inicializar columnas analíticas por defecto en el DataFrame
        df_sap["id_regla"] = None
        df_sap["tiene_regla"] = False
        df_sap["codigo"] = "SIN_CLASSIFICAR"
        df_sap["subcodigo"] = "OTROS"
        df_sap["nombre_cuenta"] = df_sap["nombre_cuenta_asociada"]
        df_sap["fecha_actualizacion"] = datetime.now()

        # Convertir columnas de texto a minúsculas en un campo temporal para búsquedas eficientes
        glosa_linea = df_sap["comentario_linea"].fillna("").str.lower()
        glosa_cabecera = df_sap["descripcion"].fillna("").str.lower()

        # 3. Evaluar regla por regla
        for regla in reglas:
            condicion = pd.Series(True, index=df_sap.index)

            if regla.cuenta:
                condicion &= df_sap["cuenta_asociada"] == regla.cuenta

            if regla.cuenta_contrapartida:
                condicion &= df_sap["cuenta_contrapartida"] == regla.cuenta_contrapartida

            if regla.centro_costo:
                condicion &= df_sap["centro_costo"] == regla.centro_costo

            if regla.filtro_texto:
                texto_buscado = regla.filtro_texto.lower()
                condicion &= glosa_linea.str.contains(texto_buscado, regex=False) | glosa_cabecera.str.contains(texto_buscado, regex=False)

            if regla.texto_excluido:
                texto_excluido = regla.texto_excluido.lower()
                condicion &= ~(glosa_linea.str.contains(texto_excluido, regex=False) | glosa_cabecera.str.contains(texto_excluido, regex=False))

            if regla.monto_min is not None:
                condicion &= df_sap["cargo_abono_ml"].astype(float) >= float(regla.monto_min)
            if regla.monto_max is not None:
                condicion &= df_sap["cargo_abono_ml"].astype(float) <= float(regla.monto_max)

            filas_a_clasificar = condicion & (df_sap["id_regla"].isna())

            if filas_a_clasificar.any():
                df_sap.loc[filas_a_clasificar, "id_regla"] = regla.id_regla
                df_sap.loc[filas_a_clasificar, "tiene_regla"] = True
                df_sap.loc[filas_a_clasificar, "codigo"] = regla.codigo
                df_sap.loc[filas_a_clasificar, "subcodigo"] = regla.subcodigo
                df_sap.loc[filas_a_clasificar, "nombre_cuenta"] = regla.nombre_cuenta

        # Convertimos a registros crudos inmediatamente (La sanitización se encarga del tipado fino)
        return df_sap.to_dict(orient="records")

    def sincronizar_carga_delta(self, desde_fecha: date, hasta_fecha: Optional[date] = None) -> int:
        """Flujo Diario/Horario: Trae modificaciones de SAP, procesa y actualiza localmente."""
        add_step(
            name="Obteniendo datos desde SAP HANA",
            message=f"desde_fecha {desde_fecha} company {self.company}",
        )
        registros_sap = self.sap_repo.get_libro_mayor_delta(desde_fecha, hasta_fecha)
        if not registros_sap:
            return 0
        
        add_step(
            name="Datos obtenidos de SAP HANA",
            message=f"cantidad_registros {len(registros_sap)}",
        )
        
        df_sap = pd.DataFrame([dict(r) for r in registros_sap])
        registros_procesados = self._ejecutar_motor_de_reglas(df_sap)
        
        # Filtrar columnas válidas del modelo
        df_limpio = pd.DataFrame(registros_procesados)
        columnas_validas_local = [col.name for col in LibroMayor.__table__.columns]
        df_limpio = df_limpio[[col for col in df_limpio.columns if col in columnas_validas_local]]

        # --- DIAGNÓSTICO Y SANITIZACIÓN ---
        # Enviamos la lista de diccionarios a limpiar antes del bulk insert
        lista_final = self._sanitizar_y_diagnosticar(df_limpio.to_dict(orient="records"))

        add_step(
            name="Guardando datos en PostgreSQL local",
            message=f"Haciendo bulk upsert de {len(lista_final)} registros.",
        )
        self.local_repo.upsert_libro_mayor_masivo(lista_final)
        return len(lista_final)

    def reprocesar_historico_local(self, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None) -> int:
        """Flujo de Corrección: Lee la BD local (NO toca SAP), re-aplica reglas y guarda."""
        add_step(
            name="Iniciando reprocesamiento de reglas locales",
            message=f"Rango: {fecha_inicio} al {fecha_fin}" if fecha_inicio else "Procesando todo el histórico local",
        )
        
        query = self.local_repo.db.query(LibroMayor)
        if fecha_inicio and fecha_fin:
            query = query.filter(LibroMayor.fecha_contabilizacion.between(fecha_inicio, fecha_fin))
            
        query_local = query.all()
        if not query_local:
            add_step(name="Reprocesamiento local terminado", message="No se encontraron registros locales en el rango.")
            return 0

        columnas_a_mantener = [
            col.name for col in LibroMayor.__table__.columns
            if col.name not in ["id_regla", "tiene_regla", "codigo", "subcodigo", "nombre_cuenta"]
        ]

        datos_locales = [{col: getattr(row, col) for col in columnas_a_mantener} for row in query_local]
        df_local = pd.DataFrame(datos_locales)

        registros_reclasificados = self._ejecutar_motor_de_reglas(df_local)
        df_final = pd.DataFrame(registros_reclasificados)
        
        ahora = datetime.now()
        df_final["updated_at"] = ahora
        df_final["updated_by"] = self.user_id

        # Asegurar columnas válidas del modelo antes del guardado masivo
        columnas_validas_local = [col.name for col in LibroMayor.__table__.columns]
        df_final = df_final[[col for col in df_final.columns if col in columnas_validas_local]]

        # --- DIAGNÓSTICO Y SANITIZACIÓN ---
        lista_final = self._sanitizar_y_diagnosticar(df_final.to_dict(orient="records"))

        self.local_repo.upsert_libro_mayor_masivo(lista_final)
        
        add_step(
            name="Reprocesamiento local completado",
            message=f"Se actualizaron exitosamente {len(lista_final)} registros analíticos.",
        )
        return len(lista_final)