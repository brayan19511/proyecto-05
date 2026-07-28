from datetime import date
import io
import logging

import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.finance.libro_mayor.libro_mayor_schema import (
    LibroMayorResponse,
    ReglaGastoCreate,
    ReglaGastoUpdate,
    SyncRequest,
    SyncDeltaRequest,
    ReprocessDateRangeRequest,
)
from app.api.finance.libro_mayor.libro_mayor_service import (
    LibroMayorService,
)
from app.api.finance.libro_mayor.service.libro_mayor_reproces_service import (
    LibroMayorReprocessService,
)

from app.api.finance.libro_mayor.service.libro_mayor_resumen_service import (
    LibroMayorResumenService,
)
from app.api.finance.libro_mayor.service.libro_mayor_job_service import (
    LibroMayorJobService,
)
from app.api.finance.libro_mayor.service.reglas_gastos_service import ReglasGastosService
from app.api.jobs.schemas import JobDetailResponse
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.core.db.db_sap import get_db_sap

logger = logging.getLogger(__name__)

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


def get_ledger_job_service(db_local=Depends(get_db)) -> LibroMayorJobService:
    return LibroMayorJobService(db_local)


def raise_bad_request(error: ValueError):
    # Mantiene el contrato historico del router sin repetir bloques try/except.
    raise HTTPException(status_code=400, detail=str(error)) from error


def raise_internal_error(detail: str, log_message: str | None = None):
    # El detalle expuesto al cliente queda controlado; el log interno es opcional.
    if log_message:
        logger.exception(log_message)
    raise HTTPException(status_code=500, detail=detail)


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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error("Error sincronizando libro mayor")


@router.post(
    "/sync-async",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_sync_libro_mayor(
    data: SyncRequest,
    batch_size: int = Query(default=1, ge=1, le=31),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: LibroMayorJobService = Depends(get_ledger_job_service),
    current_user=Depends(require_any_permission("ledger.sync", "sap.execute")),
):
    try:
        return service.enqueue_sync(
            account=data.account,
            start_date=data.start_date,
            end_date=data.end_date,
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
        )
    except ValueError as ve:
        raise_bad_request(ve)


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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error("Error sincronizando delta de libro mayor")


@router.post(
    "/sync-delta-async",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_sync_delta_libro_mayor(
    data: SyncDeltaRequest,
    batch_size: int = Query(default=1, ge=1, le=31),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: LibroMayorJobService = Depends(get_ledger_job_service),
    current_user=Depends(require_any_permission("ledger.sync", "sap.execute")),
):
    try:
        return service.enqueue_sync_delta(
            account=data.account,
            start_date=data.start_date,
            end_date=data.end_date,
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
        )
    except ValueError as ve:
        raise_bad_request(ve)


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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error("Error sincronizando delta de libro mayor")


@router.post(
    "/sync-delta-all-async",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_sync_delta_all(
    batch_size: int = Query(default=1, ge=1, le=31),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: LibroMayorJobService = Depends(get_ledger_job_service),
    current_user=Depends(require_any_permission("ledger.sync", "sap.execute")),
):
    try:
        return service.enqueue_sync_delta_all(
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
        )
    except ValueError as ve:
        raise_bad_request(ve)


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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error(
            "No se pudo reprocesar la regla",
            "Error reprocesando regla de libro mayor",
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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error(
            "No se pudo reprocesar el rango",
            "Error reprocesando rango de libro mayor",
        )


@router.post(
    "/reprocess/date-range-async",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_reprocess_date_range(
    data: ReprocessDateRangeRequest,
    batch_size: int = Query(default=1, ge=1, le=31),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: LibroMayorJobService = Depends(get_ledger_job_service),
    current_user=Depends(require_any_permission("ledger.sync", "expenses.edit")),
):
    try:
        return service.enqueue_reprocess_date_range(
            account=data.account,
            start_date=data.start_date,
            end_date=data.end_date,
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
        )
    except ValueError as ve:
        raise_bad_request(ve)


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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error(
            "No se pudo consultar el libro mayor",
            "Error consultando libro mayor",
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
        raise_bad_request(ve)

    except Exception:
        raise_internal_error(
            "No se pudo consultar el libro mayor en SAP",
            "Error consultando libro mayor en SAP",
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
        raise_bad_request(ve)

    except HTTPException:
        raise

    except Exception:
        raise_internal_error(
            "No se pudo generar el archivo Excel",
            "Error exportando libro mayor a Excel",
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
        raise_bad_request(ex)


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
        raise_bad_request(ex)


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
        raise_bad_request(ex)


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
        raise_bad_request(ex)


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
