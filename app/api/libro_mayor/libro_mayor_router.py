from datetime import date
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import pandas as pd

from app.api.libro_mayor.libro_mayor_schema import LibroMayorResponse
from app.api.libro_mayor.libro_mayor_service import LibroMayorService
from app.api.libro_mayor.service.libro_mayor_reproces_service import LibroMayorReprocessService
from app.core.db.db_postgres import get_db
from app.core.db.db_sap import get_db_sap
from app.core.security import get_current_user


router = APIRouter(prefix="/libro-mayor", tags=["LIBRO MAYOR"])


def get_libro_mayor_service(
    db_local=Depends(get_db), db_sap=Depends(get_db_sap)
) -> LibroMayorService:
    return LibroMayorService(db_local, db_sap)


def get_reprocess_service(
    db_local=Depends(get_db)
) -> LibroMayorReprocessService:

    return LibroMayorReprocessService(
        db_local=db_local
    )


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


@router.get("/reprocess/account")
def reprocess_account(
    account: str = Query(...),
    libro_mayor_reprocess: LibroMayorReprocessService = Depends(
        get_reprocess_service),
    current_user=Depends(get_current_user)
):
    try:
        return libro_mayor_reprocess.reprocess_account(account=account)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error interno en la sincronización: {str(e)}"
        )


@router.get("/reprocess/rule")
def reprocess_gasto_by_id(
    rule: int = Query(...),
    libro_mayor_reprocess: LibroMayorReprocessService = Depends(
        get_reprocess_service),
    current_user=Depends(get_current_user)
):
    try:
        return libro_mayor_reprocess.reprocess_rule(rule_id=rule)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error interno en la sincronización: {str(e)}"
        )


@router.get("/get-all", response_model=list[LibroMayorResponse], response_model_by_alias=False)
def obtenerLibroMayor(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(get_current_user)
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

@router.get("/export-excel")
def export_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(get_current_user)
):
    try:

        df = libro_mayor_service.export_excel(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail="No existen registros"
            )

        buffer = io.BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                sheet_name="Libro Mayor",
                index=False
            )

        buffer.seek(0)

        filename = (
            f"libro_mayor_"
            f"{account}_"
            f"{start_date}_"
            f"{end_date}.xlsx"
        )

        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                f'attachment; filename="{filename}"'
            }
        )

    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exportando Excel: {str(e)}"
        )
