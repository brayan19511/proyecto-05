from datetime import date
import io

import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.libro_mayor.libro_mayor_schema import (
    LibroMayorResponse,
    ReglaGastoCreate,
    ReglaGastoUpdate,
    SyncRequest,
    SyncDeltaRequest,
    ReprocessDateRangeRequest,
)
from app.api.libro_mayor.libro_mayor_service import (
    LibroMayorService,
)
from app.api.libro_mayor.service.libro_mayor_reproces_service import (
    LibroMayorReprocessService,
)

from app.api.libro_mayor.service.libro_mayor_resumen_service import (
    LibroMayorResumenService,
)
from app.api.libro_mayor.service.reglas_gastos_servive import ReglasGastosService
from app.core.db.db_postgres import get_db
from app.core.db.db_sap import get_db_sap
from app.core.security import (
    get_current_user,
)

router = APIRouter(
    prefix="/libro-mayor",
    tags=["LIBRO MAYOR"],
)


# ==========================================================
# DEPENDENCIES
# ==========================================================


def get_libro_mayor_service(
    db_local=Depends(get_db),
    db_sap=Depends(get_db_sap),
) -> LibroMayorService:
    return LibroMayorService(
        db_local=db_local,
        db_sap=db_sap,
    )


def get_reprocess_service(
    db_local=Depends(get_db),
) -> LibroMayorReprocessService:
    return LibroMayorReprocessService(
        db_local=db_local,
    )


def get_resumen_service(
    db_local=Depends(get_db),
) -> LibroMayorReprocessService:
    return LibroMayorResumenService(
        db_local=db_local,
    )


def get_permission_codes(user) -> set[str]:
    return {permission.code for permission in user.permissions}


def get_role_names(user) -> set[str]:
    return {
        link.role.name
        for link in user.user_roles_links
        if link.active
    }


def require_any_permission(*permission_codes: str):
    def checker(current_user=Depends(get_current_user)):
        if "Admin" in get_role_names(current_user):
            return current_user

        if get_permission_codes(current_user).intersection(permission_codes):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes permisos suficientes: {', '.join(permission_codes)}",
        )

    return checker


# ==========================================================
# SINCRONIZACION
# ==========================================================


@router.post("/sync")
def sync_libro_mayor(
    data: SyncRequest,
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(require_any_permission("ledger.sync", "sap.execute")),
):
    try:
        libro_mayor_service.user_id = str(current_user.id)

        return libro_mayor_service.sync(
            start_date=data.start_date,
            end_date=data.end_date,
            account=data.account,
        )

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Error sincronizando libro mayor",
        )


@router.post("/sync-delta")
def sync_delta_libro_mayor(
    data: SyncDeltaRequest,
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(require_any_permission("ledger.sync", "sap.execute")),
):
    try:
        libro_mayor_service.user_id = str(current_user.id)

        return libro_mayor_service.sync_delta(
            start_date=data.start_date,
            end_date=data.end_date,
            account=data.account,
        )

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Error sincronizando delta de libro mayor",
        )


@router.post("/sync-delta-all")
def sync_delta_all(
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(require_any_permission("ledger.sync", "sap.execute")),
):

    try:
        libro_mayor_service.user_id = str(current_user.id)

        resultados = []

        for account in ["97", "95"]:

            resultado = libro_mayor_service.sync_delta(
                account=account,
                start_date=None,
                end_date=None,
            )

            resultados.append(resultado)

        return {"accounts": resultados}

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Error sincronizando delta de libro mayor",
        )


# ==========================================================
# REPROCESAMIENTO
# ==========================================================


@router.post("/reprocess/rule/{rule_id}")
def reprocess_rule(
    rule_id: int,
    libro_mayor_reprocess: LibroMayorReprocessService = Depends(get_reprocess_service),
    current_user=Depends(require_any_permission("ledger.sync", "expenses.edit")),
):
    try:

        libro_mayor_reprocess.user_id = str(current_user.id)

        return libro_mayor_reprocess.reprocess_rule(rule_id=rule_id)

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.post("/reprocess/date-range")
def reprocess_date_range(
    data: ReprocessDateRangeRequest,
    libro_mayor_reprocess: LibroMayorReprocessService = Depends(get_reprocess_service),
    current_user=Depends(require_any_permission("ledger.sync", "expenses.edit")),
):
    try:

        libro_mayor_reprocess.user_id = str(current_user.id)

        return libro_mayor_reprocess.reprocess_date_range(
            account=data.account,
            start_date=data.start_date,
            end_date=data.end_date,
        )

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ==========================================================
# CONSULTAS
# ==========================================================


@router.get(
    "/get-all",
    response_model=list[LibroMayorResponse],
    response_model_by_alias=False,
)
def get_libro_mayor(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(require_any_permission("ledger.view", "sap.read")),
):
    try:

        return libro_mayor_service.get_libro_mayor_by_account(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get(
    "/get-by-sap",
    # response_model=list[LibroMayorResponse],
    # response_model_by_alias=False,
)
def get_libro_mayor_sap(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(require_any_permission("ledger.view", "sap.read")),
):
    try:

        return libro_mayor_service.get_libro_mayor_by_sap(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ==========================================================
# EXPORTACION
# ==========================================================


@router.get("/export-excel")
def export_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account: str = Query(...),
    libro_mayor_service: LibroMayorService = Depends(get_libro_mayor_service),
    current_user=Depends(require_any_permission("ledger.export", "ledger.view")),
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
                detail="No existen registros",
            )

        buffer = io.BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="openpyxl",
        ) as writer:

            df.to_excel(
                writer,
                sheet_name="Libro Mayor",
                index=False,
            )

        buffer.seek(0)

        filename = f"libro_mayor_" f"{account}_" f"{start_date}_" f"{end_date}.xlsx"

        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except ValueError as ve:

        raise HTTPException(
            status_code=400,
            detail=str(ve),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error exportando Excel: {str(e)}",
        )


def get_service_rule(db=Depends(get_db)):
    return ReglasGastosService(db)


@router.get("/rule")
def get_rules(
    account: str | None = Query(default=None),
    current_user=Depends(require_any_permission("expenses.view", "ledger.view")),
    service: ReglasGastosService = Depends(get_service_rule),
):
    try:

        return service.get_all(account=account)

    except ValueError as ex:
        raise HTTPException(
            status_code=400,
            detail=str(ex),
        )


@router.get("/rule/{rule_id}")
def get_rule(
    rule_id: int,
    current_user=Depends(require_any_permission("expenses.view", "ledger.view")),
    service: ReglasGastosService = Depends(get_service_rule),
):
    try:

        return service.get_by_id(rule_id)

    except ValueError as ex:
        raise HTTPException(
            status_code=404,
            detail=str(ex),
        )


@router.post("/rule")
def create_rule(
    data: ReglaGastoCreate,
    current_user=Depends(require_any_permission("expenses.edit", "expenses.edit_all")),
    service: ReglasGastosService = Depends(get_service_rule),
):
    try:

        return service.create(
            data=data,
            user_id=str(current_user.id),
        )

    except ValueError as ex:
        raise HTTPException(
            status_code=400,
            detail=str(ex),
        )


@router.put("/rule/{rule_id}")
def update_rule(
    rule_id: int,
    data: ReglaGastoUpdate,
    current_user=Depends(require_any_permission("expenses.edit", "expenses.edit_all")),
    service: ReglasGastosService = Depends(get_service_rule),
):
    try:

        return service.update(
            rule_id=rule_id,
            data=data,
            user_id=str(current_user.id),
        )

    except ValueError as ex:
        raise HTTPException(
            status_code=400,
            detail=str(ex),
        )


@router.delete("/rule/{rule_id}")
def delete_rule(
    rule_id: int,
    current_user=Depends(require_any_permission("expenses.edit", "expenses.edit_all")),
    service: ReglasGastosService = Depends(get_service_rule),
):
    try:

        return service.delete(
            rule_id=rule_id,
            user_id=str(current_user.id),
        )

    except ValueError as ex:
        raise HTTPException(
            status_code=400,
            detail=str(ex),
        )


# summary


@router.get("/summary")
def get_summary(
    start_date: date,
    end_date: date,
    account: str,
    current_user=Depends(require_any_permission("ledger.view", "expenses.view")),
    service: LibroMayorResumenService = Depends(get_resumen_service),
):

    return service.get_resumen(
        start_date=start_date,
        end_date=end_date,
        account=account,
    )


@router.get(
    "/summary-detail",
    response_model=list[LibroMayorResponse],
    response_model_by_alias=False,
)
def get_summary_detail(
    start_date: date,
    end_date: date,
    account: str,
    codigo: str | None = None,
    subcodigo: str | None = None,
    proveedor: str | None = None,
    anio: int | None = None,
    mes: int | None = None,
    current_user=Depends(require_any_permission("ledger.view", "expenses.view")),
    service: LibroMayorResumenService = Depends(get_resumen_service),
):

    return service.get_detalle(
        start_date=start_date,
        end_date=end_date,
        account=account,
        codigo=codigo,
        subcodigo=subcodigo,
        proveedor=proveedor,
        anio=anio,
        mes=mes,
    )
