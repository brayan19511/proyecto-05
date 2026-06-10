from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.libro_mayor.libro_mayor_schema import LibroMayorResponse
from app.api.libro_mayor.libro_mayor_service import LibroMayorService
from app.core.db.db_postgres import get_db
from app.core.db.db_sap import get_db_sap

router = APIRouter(prefix="/libro-mayor", tags=["LIBRO MAYOR"])


def get_libro_mayor_service(
    db_local=Depends(get_db), db_sap=Depends(get_db_sap)
) -> LibroMayorService:
    return LibroMayorService(db_local, db_sap)


@router.get("/sync-date")
def sincronizacion(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
):
    try:
        return libro_mayor_service.sync(
            start_date=start_date, end_date=end_date, account=account
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error interno en la sincronización: {str(e)}"
        )

@router.get("/sync-delta")
def sincronizacion_detlta(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
):
    try:
        return libro_mayor_service.sync_delta(
            start_date=start_date, end_date=end_date, account=account
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error interno en la sincronización: {str(e)}"
        )

@router.get("/get-all", response_model=list[LibroMayorResponse],response_model_by_alias=False)
def obtenerLibroMayor(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
):
    try:
        return libro_mayor_service.get_libro_mayor_by_account(
            start_date=start_date, end_date=end_date, account=account
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error interno en la sincronización: {str(e)}"
        )
