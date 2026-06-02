# app/api/coolbox/ventas/ventas_router.py
from fastapi import APIRouter, Depends, status
from datetime import date
from app.api.coolbox.ventas.service.productos_service import ProductosService
from app.api.coolbox.ventas.service.ventas_service import VentasService
from app.core.db.db_coolbox import get_db_coolbox
from app.core.db.db_postgres import get_db # Asegúrate de tener este generator

router = APIRouter(
    tags=["Procesamiento Ventas"],
)

@router.get("/procesar-ventas", status_code=status.HTTP_201_CREATED)
async def procesar_ventas_por_fecha(
    fecha: date, 
    db_fuente=Depends(get_db_coolbox), 
    db_destino=Depends(get_db)
):
    # Pasamos ambas conexiones al servicio
    service = VentasService(db_fuente=db_fuente, db_destino=db_destino)
    resultado = service.ejecutar_etl_ventas(fecha)
    return resultado
@router.get("/procesar-ventas-rango", status_code=status.HTTP_201_CREATED)
async def procesar_ventas_por_rango(
    fecha_inicio: date,
    fecha_fin: date,
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db)
):
    # Pasamos ambas conexiones al servicio
    service = VentasService(db_fuente=db_fuente, db_destino=db_destino)
    resultado = service.ejecutar_etl_ventas_rango(fecha_inicio, fecha_fin)
    return resultado
@router.get("/procesar-catalogo", status_code=status.HTTP_201_CREATED)
async def procesar_productos(
    db_fuente=Depends(get_db_coolbox),
    db_destino=Depends(get_db)
):
    service = ProductosService(db_fuente=db_fuente, db_destino=db_destino)
    return service.ejecutar_etl_productos()