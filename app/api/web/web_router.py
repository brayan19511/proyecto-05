# app\api\sap\finance\sap_finance_router.py
from datetime import date
import io
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query,Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from sqlalchemy.orm import Session

from app.core.db.db_postgres import get_db
from app.core.db.db_sap import get_db_sap
from app.models.finance.libro_mayor_model import LibroMayor, ReglasGastos

router = APIRouter(prefix="/web", tags=["WEB"])
    
templates = Jinja2Templates(directory="app/api/web/template")
# PÁGINA 1: GESTIÓN DE REGLAS
@router.get("/reglas", response_class=HTMLResponse)
def vista_crud_reglas(request: Request):
    # En las nuevas versiones, se pasa el request directo y los datos van en un diccionario plano después
    return templates.TemplateResponse(
        request, 
        "reglas_crud.html", 
        {"active_page": "reglas"}
    )


# PÁGINA 2: DESCARGA DE REPORTES EXCEL
@router.get("/libro-mayor", response_class=HTMLResponse)
def vista_descargar_reporte(request: Request):
    # Lo mismo aquí: request, nombre de la plantilla, y los datos limpios
    return templates.TemplateResponse(
        request, 
        "descargar_reporte.html", 
        {"active_page": "descargar"}
    )