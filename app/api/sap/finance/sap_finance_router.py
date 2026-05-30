# app\api\sap\finance\sap_finance_router.py
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.sap.finance.sap_finance_service import SapFinanceService
from app.core.db_sap import get_db_sap

router = APIRouter(prefix="/finance", tags=["SAP FINANCE"])


def get_sap_finance_service(db=Depends(get_db_sap)):
    return SapFinanceService(db)


@router.get("/libro-mayor")
def get_libro_mayor_account(
    start_date: date,
    end_date: date,
    account: str,
    service: SapFinanceService = Depends(get_sap_finance_service),
):

    return service.get_libro_mayor_account(start_date, end_date, account)
@router.get("/libro-mayor/exportar-excel")
def exportar_libro_mayor_excel(
    start_date: date,
    end_date: date,
    account: str,
    service: SapFinanceService = Depends(get_sap_finance_service),
):
    # 1. Obtener los bytes del archivo Excel procesado desde el servicio
    excel_buffer = service.export_libro_mayor_to_excel_v2(start_date, end_date, account)
    
    # 2. Retornar el archivo binario al cliente mediante streaming
    filename = f"Libro_Mayor_{account}_{start_date}_al_{end_date}.xlsx"
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )