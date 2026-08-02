from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.api.jobs.constants import JobType
from app.api.jobs.service import JobService
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.analytics import AnalyticsIngestionItem, AnalyticsIngestionRun
from app.services.ingestion.catalog import (
    ICG_TABLES,
    IcgTableConfig,
    MasterStorageMode,
    TableKind,
    get_icg_table_config,
)


class AnalyticsIngestionService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue_icg_table(
        self,
        *,
        table_name: str,
        mode: str,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        lookback_days: int | None = None,
        batch_size: int = 1,
        idempotency_key: str | None = None,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        return self.enqueue_icg_tables(
            table_names=[table_name],
            mode=mode,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            lookback_days=lookback_days,
            batch_size=batch_size,
            idempotency_key=idempotency_key,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
        )

    def enqueue_icg_tables(
        self,
        *,
        table_names: list[str],
        mode: str,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        lookback_days: int | None = None,
        batch_size: int = 1,
        idempotency_key: str | None = None,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        table_configs = self._resolve_table_configs(table_names)
        if not table_configs:
            raise ValidationError("Debe indicar al menos una tabla ICG")

        runs: list[AnalyticsIngestionRun] = []
        payloads: dict[str, dict] = {}
        normalized_mode = mode.lower()

        for table_config in table_configs:
            run, run_payloads = self._prepare_run(
                table_config=table_config,
                mode=normalized_mode,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                lookback_days=lookback_days,
            )
            runs.append(run)
            overlap = set(payloads).intersection(run_payloads)
            if overlap:
                raise ValidationError("Hay referencias duplicadas en la ingesta ICG")
            payloads.update(run_payloads)

        from app.workers.dispatcher import dispatch_job

        job = JobService(self.db, dispatcher=dispatch_job).create_job(
            job_type=JobType.ANALYTICS_EXTRACT.value,
            parameters={
                "source": "icg",
                "table_names": [table.name for table in table_configs],
                "mode": normalized_mode,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "lookback_days": lookback_days,
            },
            references=list(payloads),
            user_id=user_id,
            batch_size=batch_size,
            idempotency_key=idempotency_key,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source or "API",
            item_payloads=payloads,
        )
        for run in runs:
            run.job_id = job.id
        self.db.commit()
        return job

    def _prepare_run(
        self,
        *,
        table_config: IcgTableConfig,
        mode: str,
        user_id: UUID,
        start_date: date | None,
        end_date: date | None,
        lookback_days: int | None,
    ) -> tuple[AnalyticsIngestionRun, dict[str, dict]]:
        resolved_start, resolved_end = self._resolve_dates(
            table_kind=table_config.kind,
            mode=mode,
            start_date=start_date,
            end_date=end_date,
            lookback_days=lookback_days,
        )

        run = AnalyticsIngestionRun(
            source_code="icg",
            table_name=table_config.name,
            table_kind=table_config.kind.value,
            mode=mode,
            status="CREATED",
            start_date=resolved_start,
            end_date=resolved_end,
            parameters={
                "master_storage_mode": (
                    table_config.master_storage_mode.value
                    if table_config.master_storage_mode
                    else None
                ),
            },
            created_by=user_id,
        )
        self.db.add(run)
        self.db.flush()

        payloads = self._build_payloads(run, table_config)
        for reference, payload in payloads.items():
            run.items.append(
                AnalyticsIngestionItem(
                    reference=reference,
                    business_date=self._parse_date(payload.get("business_date")),
                    status="PENDING",
                )
            )

        return run, payloads

    @staticmethod
    def _resolve_table_configs(table_names: list[str]) -> list[IcgTableConfig]:
        normalized = list(dict.fromkeys(name.strip().lower() for name in table_names if name.strip()))
        return [get_icg_table_config(name) for name in normalized]

    @staticmethod
    def get_icg_table_names_by_group(table_group: str) -> list[str]:
        normalized = table_group.strip().lower()
        if normalized == "transactional":
            return [
                table.name
                for table in ICG_TABLES.values()
                if table.kind == TableKind.TRANSACTIONAL
            ]
        if normalized == "master":
            return [
                table.name
                for table in ICG_TABLES.values()
                if table.kind == TableKind.MASTER
            ]
        if normalized == "all":
            return [table.name for table in ICG_TABLES.values()]
        raise ValidationError("table_group debe ser transactional, master o all")

    def _resolve_dates(
        self,
        *,
        table_kind: TableKind,
        mode: str,
        start_date: date | None,
        end_date: date | None,
        lookback_days: int | None,
    ) -> tuple[date | None, date | None]:
        if table_kind == TableKind.MASTER:
            if mode != "snapshot":
                raise ValidationError(
                    "Las tablas maestras no soportan incremental; usa mode=snapshot"
                )
            if start_date or end_date:
                raise ValidationError(
                    "Las tablas maestras no usan start_date ni end_date"
                )
            return None, None

        today = self._today()
        if mode == "snapshot":
            raise ValidationError(
                "Las tablas transaccionales no soportan snapshot; usa incremental o reprocess"
            )
        if mode == "incremental":
            resolved_lookback_days = (
                settings.ICG_INCREMENTAL_LOOKBACK_DAYS
                if lookback_days is None
                else lookback_days
            )
            if resolved_lookback_days < 0:
                raise ValidationError("lookback_days no puede ser negativo")
            resolved_start = (
                start_date
                or today - timedelta(days=resolved_lookback_days)
            )
            resolved_end = end_date or today
            self._validate_resolved_range(
                start_date=resolved_start,
                end_date=resolved_end,
                today=today,
            )
            return resolved_start, resolved_end
        if mode == "reprocess":
            if not start_date or not end_date:
                raise ValidationError("start_date y end_date son obligatorios para reproceso")
            self._validate_resolved_range(
                start_date=start_date,
                end_date=end_date,
                today=today,
            )
            return start_date, end_date
        raise ValidationError("Modo no soportado para tabla transaccional")

    def _build_payloads(self, run: AnalyticsIngestionRun, table_config) -> dict[str, dict]:
        if table_config.kind == TableKind.MASTER:
            storage_mode = table_config.master_storage_mode or MasterStorageMode.LATEST
            reference = f"icg:{table_config.name}:{storage_mode.value}"
            return {
                reference: {
                    "source": "icg",
                    "table_name": table_config.name,
                    "table_kind": table_config.kind.value,
                    "mode": run.mode,
                    "master_storage_mode": storage_mode.value,
                    "ingestion_run_id": str(run.id),
                }
            }

        payloads = {}
        current = run.start_date
        while current and run.end_date and current <= run.end_date:
            reference = f"icg:{table_config.name}:{current.isoformat()}"
            payloads[reference] = {
                "source": "icg",
                "table_name": table_config.name,
                "table_kind": table_config.kind.value,
                "mode": run.mode,
                "business_date": current.isoformat(),
                "ingestion_run_id": str(run.id),
            }
            current += timedelta(days=1)
        return payloads

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        return date.fromisoformat(value) if value else None

    @staticmethod
    def _today() -> date:
        return datetime.now(ZoneInfo("America/Lima")).date()

    @staticmethod
    def _validate_resolved_range(
        *,
        start_date: date,
        end_date: date,
        today: date,
    ) -> None:
        if end_date < start_date:
            raise ValidationError("end_date no puede ser menor que start_date")
        if start_date > today or end_date > today:
            raise ValidationError(
                f"No se permiten fechas futuras para ICG; la fecha maxima es {today.isoformat()}"
            )
