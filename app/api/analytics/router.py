from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.analytics.schemas import (
    IcgCatalogResponse,
    IcgIngestionRequest,
    IcgSilverBuildRequest,
    IcgTableResponse,
)
from app.api.jobs.constants import (
    ANALYTICS_INGEST_RUN_PERMISSION,
    ANALYTICS_INGEST_VIEW_PERMISSION,
)
from app.api.jobs.schemas import JobDetailResponse
from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db
from app.services.analytics_queries import IcgSalesAnalyticsQuery
from app.services.analytics_silver.orchestrator import AnalyticsSilverJobService
from app.services.ingestion.catalog import ICG_TABLES
from app.services.ingestion.orchestrator import AnalyticsIngestionService


router = APIRouter(prefix="/analytics", tags=["ANALYTICS"])


def get_ingestion_service(db: Session = Depends(get_db)) -> AnalyticsIngestionService:
    return AnalyticsIngestionService(db)


def get_silver_job_service(db: Session = Depends(get_db)) -> AnalyticsSilverJobService:
    return AnalyticsSilverJobService(db)


def get_sales_query_service() -> IcgSalesAnalyticsQuery:
    return IcgSalesAnalyticsQuery()


@router.get("/icg/tables", response_model=IcgCatalogResponse)
def list_icg_tables(
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return IcgCatalogResponse(
        items=[
            IcgTableResponse(
                name=config.name,
                kind=config.kind.value,
                master_storage_mode=(
                    config.master_storage_mode.value
                    if config.master_storage_mode
                    else None
                ),
            )
            for config in ICG_TABLES.values()
        ]
    )


@router.post(
    "/icg/ingestions",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_icg_ingestion(
    data: IcgIngestionRequest,
    service: AnalyticsIngestionService = Depends(get_ingestion_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_RUN_PERMISSION)),
):
    if data.table_group:
        table_names = service.get_icg_table_names_by_group(data.table_group)
    elif data.table_names:
        table_names = data.table_names
    else:
        table_names = [data.table_name]

    return service.enqueue_icg_tables(
        table_names=table_names,
        mode=data.mode.value,
        start_date=data.start_date,
        end_date=data.end_date,
        lookback_days=data.lookback_days,
        batch_size=data.batch_size,
        idempotency_key=data.idempotency_key,
        user_id=current_user.id,
    )


@router.post(
    "/icg/silver/sales",
    response_model=JobDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def build_icg_sales_silver(
    data: IcgSilverBuildRequest,
    service: AnalyticsSilverJobService = Depends(get_silver_job_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_RUN_PERMISSION)),
):
    return service.enqueue_icg_sales_build(
        start_date=data.start_date,
        end_date=data.end_date or data.start_date,
        batch_size=data.batch_size,
        idempotency_key=data.idempotency_key,
        user_id=current_user.id,
    )


@router.get("/icg/sales/summary")
def get_icg_sales_summary(
    start_date: date,
    end_date: date,
    channel: str | None = None,
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return service.summary(
        start_date=start_date,
        end_date=end_date,
        channel=channel,
    )


@router.get("/icg/sales/by-channel")
def get_icg_sales_by_channel(
    start_date: date,
    end_date: date,
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.by_channel(start_date=start_date, end_date=end_date)
    }


@router.get("/icg/sales/ecommerce")
def get_icg_sales_ecommerce(
    start_date: date,
    end_date: date,
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.ecommerce_performance(start_date=start_date, end_date=end_date),
    }


@router.get("/icg/sales/by-store")
def get_icg_sales_by_store(
    start_date: date,
    end_date: date,
    limit: int = Query(default=20, ge=1, le=500),
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.by_store(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    }


@router.get("/icg/sales/by-seller")
def get_icg_sales_by_seller(
    start_date: date,
    end_date: date,
    limit: int = Query(default=20, ge=1, le=500),
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.by_seller(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    }


@router.get("/icg/products/abc")
def get_icg_product_abc(
    start_date: date,
    end_date: date,
    limit: int = Query(default=100, ge=1, le=1000),
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.product_abc(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    }


@router.get("/icg/products/low-movement")
def get_icg_product_low_movement(
    start_date: date,
    end_date: date,
    limit: int = Query(default=100, ge=1, le=1000),
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.product_low_movement(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        ),
        "note": "Bajo movimiento comercial segun ventas del rango; para rotacion de inventario falta silver central de movimientos/kardex.",
    }


@router.get("/icg/customers/rfm")
def get_icg_customer_rfm(
    start_date: date,
    end_date: date,
    limit: int = Query(default=100, ge=1, le=1000),
    service: IcgSalesAnalyticsQuery = Depends(get_sales_query_service),
    current_user=Depends(require_any_permission(ANALYTICS_INGEST_VIEW_PERMISSION)),
):
    return {
        "items": service.rfm(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    }
