from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.finance.libro_mayor.libro_mayor_service import SUPPORTED_ACCOUNTS
from app.api.finance.libro_mayor.repository.libro_mayor_repository import (
    LibroMayorRepository,
)
from app.api.jobs.constants import JobType
from app.api.jobs.service import JobService
from app.workers.dispatcher import dispatch_job


DEFAULT_LEDGER_START_DATE = date(2026, 1, 1)
DEFAULT_LEDGER_ACCOUNTS = ("97", "95")


class LibroMayorJobService:
    """Crea jobs pequenos e idempotentes para procesos pesados de libro mayor."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = LibroMayorRepository(db)

    def enqueue_sync(
        self,
        *,
        account: str,
        start_date: date,
        end_date: date,
        user_id: UUID,
        idempotency_key: str | None = None,
        batch_size: int = 1,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        self._validate_account(account)
        payloads = self._build_daily_payloads(
            operation="sync",
            accounts=[account],
            start_date=start_date,
            end_date=end_date,
        )
        return self._create_job(
            job_type=JobType.LEDGER_SYNC.value,
            parameters={
                "operation": "sync",
                "account": account,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            payloads=payloads,
            user_id=user_id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
        )

    def enqueue_sync_delta(
        self,
        *,
        account: str,
        start_date: date | None,
        end_date: date | None,
        user_id: UUID,
        idempotency_key: str | None = None,
        batch_size: int = 1,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        self._validate_account(account)
        resolved_start = self._resolve_delta_start(account, start_date)
        resolved_end = end_date or date.today()
        payloads = self._build_daily_payloads(
            operation="sync_delta",
            accounts=[account],
            start_date=resolved_start,
            end_date=resolved_end,
        )
        return self._create_job(
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            parameters={
                "operation": "sync_delta",
                "account": account,
                "start_date": resolved_start.isoformat(),
                "end_date": resolved_end.isoformat(),
            },
            payloads=payloads,
            user_id=user_id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
        )

    def enqueue_sync_delta_all(
        self,
        *,
        user_id: UUID,
        idempotency_key: str | None = None,
        batch_size: int = 1,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        payloads = {}
        parameters = {"operation": "sync_delta_all", "accounts": []}
        for account in DEFAULT_LEDGER_ACCOUNTS:
            start_date = self._resolve_delta_start(account, None)
            end_date = date.today()
            parameters["accounts"].append(
                {
                    "account": account,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                }
            )
            payloads.update(
                self._build_daily_payloads(
                    operation="sync_delta",
                    accounts=[account],
                    start_date=start_date,
                    end_date=end_date,
                )
            )

        return self._create_job(
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            parameters=parameters,
            payloads=payloads,
            user_id=user_id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
        )

    def enqueue_reprocess_date_range(
        self,
        *,
        account: str,
        start_date: date,
        end_date: date,
        user_id: UUID,
        idempotency_key: str | None = None,
        batch_size: int = 1,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        self._validate_account(account)
        payloads = self._build_daily_payloads(
            operation="reprocess",
            accounts=[account],
            start_date=start_date,
            end_date=end_date,
        )
        return self._create_job(
            job_type=JobType.LEDGER_REPROCESS.value,
            parameters={
                "operation": "reprocess",
                "account": account,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            payloads=payloads,
            user_id=user_id,
            idempotency_key=idempotency_key,
            batch_size=batch_size,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
        )

    def _create_job(
        self,
        *,
        job_type: str,
        parameters: dict,
        payloads: dict[str, dict],
        user_id: UUID,
        idempotency_key: str | None,
        batch_size: int,
        scheduled_job_id: UUID | None = None,
        trigger_source: str | None = None,
    ):
        kwargs = {}
        if trigger_source:
            kwargs["trigger_source"] = trigger_source

        return JobService(self.db, dispatcher=dispatch_job).create_job(
            job_type=job_type,
            parameters=parameters,
            references=list(payloads),
            user_id=user_id,
            batch_size=batch_size,
            idempotency_key=idempotency_key,
            scheduled_job_id=scheduled_job_id,
            item_payloads=payloads,
            **kwargs,
        )

    def _resolve_delta_start(self, account: str, start_date: date | None) -> date:
        if start_date:
            return start_date

        last_record = self.repository.get_last_libro_mayor(account)
        if not last_record:
            return DEFAULT_LEDGER_START_DATE

        # Usamos la fecha completa del ultimo cambio conocido. El upsert hace
        # segura una pequena superposicion si SAP devuelve filas ya cargadas.
        return last_record.fecha_actualizacion.date()

    def _build_daily_payloads(
        self,
        *,
        operation: str,
        accounts: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, dict]:
        if end_date < start_date:
            raise ValueError("La fecha fin no puede ser menor a la fecha inicio")

        payloads = {}
        current = start_date
        while current <= end_date:
            for account in accounts:
                reference = f"{operation}:{account}:{current.isoformat()}"
                payloads[reference] = {
                    "operation": operation,
                    "account": account,
                    "start_date": current.isoformat(),
                    "end_date": current.isoformat(),
                }
            current += timedelta(days=1)
        return payloads

    @staticmethod
    def _validate_account(account: str) -> None:
        if account not in SUPPORTED_ACCOUNTS:
            raise ValueError(f"Cuenta no soportada: {account}")
