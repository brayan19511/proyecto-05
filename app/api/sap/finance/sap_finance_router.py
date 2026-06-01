# app\api\sap\finance\sap_finance_router.py
from datetime import date
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query,Request
from fastapi.responses import StreamingResponse
import pandas as pd
from sqlalchemy.orm import Session

from app.api.sap.finance.sap_finance_schema import ReglaGastoCreate, ReglaGastoResponse
from app.api.sap.finance.sap_finance_service import SapFinanceService
from app.core.db.db_postgres import get_db
from app.core.db.db_sap import get_db_sap
from app.models.finance.libro_mayor_model import LibroMayor, ReglasGastos

router = APIRouter(prefix="/finance", tags=["SAP FINANCE"])


def get_sap_finance_service(db=Depends(get_db_sap)):
    return SapFinanceService(db)

@router.get("/sync-delta")
def sincronizar_delta(
    desde_fecha: date = Query(..., description="Fecha de corte para buscar cambios en SAP (YYYY-MM-DD)"),
    company: str = Query("SBO_RASH_PRODUCCION", description="Base de datos de SAP a consultar"),
    db_local= Depends(get_db),
    db_sap= Depends(get_db_sap)
):
    """
    Sincroniza de forma incremental los registros del Libro Mayor de SAP.
    Busca transacciones creadas o editadas en SAP desde la fecha indicada,
    les aplica las reglas vigentes y hace un UPSERT masivo local.
    """
    try:
        service = SapFinanceService(db_sap=db_sap, db_local=db_local, company=company)
        total_procesados = service.sincronizar_carga_delta(desde_fecha)
        return {
            "status": "success",
            "message": f"Sincronización delta finalizada con éxito.",
            "registros_procesados": total_procesados
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno en la sincronización: {str(e)}")
    
@router.get("/reprocesar", status_code=200)
def reprocesar_reglas_locales(
    # Cambiamos ... por None para hacerlos opcionales en el Swagger de FastAPI
    request: Request,
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicial opcional (YYYY-MM-DD). Si se omite, procesa todo."),
    fecha_fin: Optional[date] = Query(None, description="Fecha final opcional (YYYY-MM-DD). Si se omite, procesa todo."),
    company: str = Query("SBO_RASH_PRODUCCION"),
    db_local = Depends(get_db),
    db_sap = Depends(get_db_sap)
):
    try:
        # Validar que si mandan una fecha, obligatoriamente manden la otra
        if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
            raise HTTPException(status_code=400, detail="Debes enviar ambas fechas o ninguna.")

        # Extraemos el usuario del state si lo tienes en el middleware de auth
        user_id = getattr(request.state, "user_id", None)

        service = SapFinanceService(db_sap=db_sap, db_local=db_local, company=company, user_id=user_id)
        total_reprocesados = service.reprocesar_historico_local(fecha_inicio, fecha_fin)
        
        rango_msg = f"del rango {fecha_inicio} al {fecha_fin}" if fecha_inicio else "de todo el histórico"
        return {
            "status": "success",
            "message": f"Reprocesamiento completado con éxito {rango_msg}.",
            "registros_actualizados": total_reprocesados
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reprocesar: {str(e)}")
    
@router.get("/libro-mayor/exportar-excel")
def exportar_libro_mayor_excel(
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db_local= Depends(get_db)
):
    try:
        # 1. Consultar la data de Postgres local
        query = db_local.query(LibroMayor)
        if fecha_inicio and fecha_fin:
            query = query.filter(LibroMayor.fecha_contabilizacion.between(fecha_inicio, fecha_fin))
        
        registros = query.all()
        if not registros:
            raise HTTPException(status_code=44, detail="No hay datos para exportar en este rango.")

        # 2. Convertir a DataFrame de Pandas
        # Obtenemos todas las columnas del modelo de forma dinámica
        columnas = [col.name for col in LibroMayor.__table__.columns]
        data = [{col: getattr(row, col) for col in columnas} for row in registros]
        df = pd.DataFrame(data)

        # Formatear fechas para que Excel las entienda limpiamente
        for col in df.columns:
            if df[col].dtype == 'object' and col in ['fecha_contabilizacion', 'fecha_documento', 'created_at']:
                df[col] = df[col].astype(str)

        # 3. Escribir el DataFrame en un buffer de memoria como archivo Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Libro Mayor Analítico')
        
        buffer.seek(0)
        
        # 4. Retornar el flujo de datos para descarga inmediata en el navegador/app
        filename = f"libro_mayor_{fecha_inicio or 'historico'}_{fecha_fin or 'actual'}.xlsx"
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar Excel: {str(e)}")    
    
    
    
    
    
@router.get("/gasto/", response_model=List[ReglaGastoResponse])
def listar_reglas(db: Session = Depends(get_db)):
    return db.query(ReglasGastos).order_by(ReglasGastos.prioridad.asc()).all()

@router.post("/gasto/", response_model=ReglaGastoResponse)
def crear_regla(payload: ReglaGastoCreate, db: Session = Depends(get_db)):
    nueva_regla = ReglasGastos(**payload.dict())
    db.add(nueva_regla)
    db.commit()
    db.refresh(nueva_regla)
    return nueva_regla

@router.put("/gasto/{regla_id}", response_model=ReglaGastoResponse)
def actualizar_regla(regla_id: int, payload: ReglaGastoCreate, db: Session = Depends(get_db)):
    regla = db.query(ReglasGastos).filter(ReglasGastos.id_regla == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    for key, value in payload.dict().items():
        setattr(regla, key, value)
    db.commit()
    db.refresh(regla)
    return regla

@router.delete("/gasto/{regla_id}")
def eliminar_regla(regla_id: int, db: Session = Depends(get_db)):
    regla = db.query(ReglasGastos).filter(ReglasGastos.id_regla == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    db.delete(regla)
    db.commit()
    return {"status": "success", "message": "Regla eliminada correctamente"}
    
    
    
# @router.get("/libro-mayor")
# def get_libro_mayor_account(
#     start_date: date,
#     end_date: date,
#     account: str,
#     service: SapFinanceService = Depends(get_sap_finance_service),
# ):

#     return service.get_libro_mayor_account(start_date, end_date, account)
# @router.get("/libro-mayor/exportar-excel")
# def exportar_libro_mayor_excel(
#     start_date: date,
#     end_date: date,
#     account: str,
#     service: SapFinanceService = Depends(get_sap_finance_service),
# ):
#     # 1. Obtener los bytes del archivo Excel procesado desde el servicio
#     excel_buffer = service.export_libro_mayor_to_excel_v2(start_date, end_date, account)
    
#     # 2. Retornar el archivo binario al cliente mediante streaming
#     filename = f"Libro_Mayor_{account}_{start_date}_al_{end_date}.xlsx"
#     return StreamingResponse(
#         excel_buffer,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={"Content-Disposition": f"attachment; filename={filename}"}
#     )