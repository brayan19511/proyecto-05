from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.finance.libro_mayor.service.libro_mayor_job_service import (
    LibroMayorJobService,
)
from app.api.jobs.constants import JobTriggerSource, JobType
from app.api.scheduled_jobs.repository import ScheduledJobRepository
from app.api.scheduled_jobs.schedule import (
    calculate_next_run,
    validate_timezone,
)
from app.api.scheduled_jobs.schemas import (
    ScheduledJobCreate,
    ScheduledJobPageResponse,
    ScheduledJobUpdate,
    validate_schedule_config,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.jobs import Job, ScheduledJob
from app.services.ingestion.orchestrator import AnalyticsIngestionService


class ScheduledJobService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ScheduledJobRepository(db)

    def create(self, data: ScheduledJobCreate, *, user_id: UUID) -> ScheduledJob:
        validate_timezone(data.timezone)
        next_run_at = data.next_run_at or calculate_next_run(
            schedule_kind=data.schedule_kind.value,
            schedule_config=data.schedule_config,
            tz_name=data.timezone,
        )
        scheduled_job = ScheduledJob(
            name=data.name,
            job_type=data.job_type.value,
            enabled=data.enabled,
            schedule_kind=data.schedule_kind.value,
            schedule_config=data.schedule_config,
            parameters=data.parameters,
            batch_size=data.batch_size,
            timezone=data.timezone,
            next_run_at=next_run_at,
            created_by=user_id,
        )
        self.db.add(scheduled_job)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ConflictError("Ya existe una tarea programada con ese nombre") from error
        return scheduled_job

    def list_jobs(
        self,
        *,
        enabled: bool | None,
        limit: int,
        offset: int,
    ) -> ScheduledJobPageResponse:
        items, total = self.repository.list_jobs(
            enabled=enabled,
            limit=limit,
            offset=offset,
        )
        return ScheduledJobPageResponse.build(items, total, limit, offset)

    def get(self, scheduled_job_id: UUID) -> ScheduledJob:
        scheduled_job = self.repository.get_by_id(scheduled_job_id)
        if not scheduled_job:
            raise NotFoundError("Tarea programada no encontrada")
        return scheduled_job

    def update(
        self,
        scheduled_job_id: UUID,
        data: ScheduledJobUpdate,
        *,
        user_id: UUID,
    ) -> ScheduledJob:
        scheduled_job = self.get(scheduled_job_id)
        updates = data.model_dump(exclude_unset=True)
        if "timezone" in updates:
            validate_timezone(updates["timezone"])

        for field, value in updates.items():
            normalized = value.value if hasattr(value, "value") else value
            setattr(scheduled_job, field, normalized)

        # Valida la configuracion resultante tras el merge, para que un PATCH
        # parcial no deje una agenda invalida (p.ej. DAILY sin times) que luego
        # rompa el calculo del proximo disparo.
        if {"schedule_kind", "schedule_config"}.intersection(updates):
            try:
                validate_schedule_config(
                    scheduled_job.schedule_kind,
                    scheduled_job.schedule_config,
                )
            except ValueError as error:
                raise ValidationError(str(error)) from error

        if "next_run_at" not in updates and {
            "schedule_kind",
            "schedule_config",
            "timezone",
        }.intersection(updates):
            scheduled_job.next_run_at = calculate_next_run(
                schedule_kind=scheduled_job.schedule_kind,
                schedule_config=scheduled_job.schedule_config,
                tz_name=scheduled_job.timezone,
            )

        scheduled_job.updated_by = user_id
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ConflictError("Ya existe una tarea programada con ese nombre") from error
        return scheduled_job

    def run_now(self, scheduled_job_id: UUID, *, user_id: UUID) -> Job:
        scheduled_job = self.get(scheduled_job_id)
        scheduled_job.last_run_at = datetime.now(timezone.utc)
        return self._create_execution(
            scheduled_job,
            due_at=scheduled_job.last_run_at,
            manual=True,
            user_id=user_id,
        )

    def run_due(self, *, limit: int = 20) -> int:
        executed = 0
        for _ in range(limit):
            now = datetime.now(timezone.utc)
            due_jobs = self.repository.list_due_jobs(now=now, limit=1)
            if not due_jobs:
                break
            if self._advance_and_execute(due_jobs[0], now=now):
                executed += 1
        return executed

    def _advance_and_execute(self, scheduled_job: ScheduledJob, *, now: datetime) -> bool:
        """Avanza el proximo disparo y lanza la ejecucion de una tarea vencida.

        Cualquier fallo se aisla en esta tarea para que una sola tarea "veneno"
        no bloquee al resto de tareas vencidas:
        - Si el schedule_config es invalido y no se puede calcular next_run_at,
          la tarea se deshabilita (sale de la cola de vencidas) y el operador la
          revisa por last_error.
        - Si falla el despacho, next_run_at ya avanzo, asi que no se reintenta de
          inmediato; el error queda registrado en la tarea programada.
        """
        due_at = scheduled_job.next_run_at
        scheduled_job.last_run_at = now
        try:
            scheduled_job.next_run_at = calculate_next_run(
                schedule_kind=scheduled_job.schedule_kind,
                schedule_config=scheduled_job.schedule_config,
                tz_name=scheduled_job.timezone,
                after=now,
            )
        except Exception as error:
            scheduled_job.enabled = False
            scheduled_job.last_status = "FAILED"
            scheduled_job.last_error = f"schedule_config invalido: {error}"[:1000]
            scheduled_job.consecutive_failures += 1
            self.db.commit()
            return False

        self.db.commit()
        try:
            self._create_execution(scheduled_job, due_at=due_at, manual=False)
            return True
        except Exception:
            return False

    def _create_execution(
        self,
        scheduled_job: ScheduledJob,
        *,
        due_at: datetime,
        manual: bool,
        user_id: UUID | None = None,
    ) -> Job:
        if not scheduled_job.created_by:
            raise ValidationError("La tarea programada no tiene usuario creador")

        idempotency_key = self._build_idempotency_key(scheduled_job, due_at, manual)
        # Una ejecucion manual se atribuye al usuario que la forzo. La ejecucion
        # automatica usa el creador de la programacion como usuario funcional.
        execution_user_id = user_id if manual and user_id else scheduled_job.created_by
        trigger_source = (
            JobTriggerSource.SCHEDULED_MANUAL.value
            if manual
            else JobTriggerSource.SCHEDULED.value
        )
        try:
            job = self._dispatch_scheduled_job(
                scheduled_job,
                idempotency_key=idempotency_key,
                user_id=execution_user_id,
                trigger_source=trigger_source,
            )
            scheduled_job.last_job_id = job.id
            scheduled_job.last_status = job.status
            scheduled_job.last_error = None
            scheduled_job.consecutive_failures = 0
            self.db.commit()
            return job
        except Exception as error:
            scheduled_job.last_status = "FAILED"
            scheduled_job.last_error = str(error)[:1000]
            scheduled_job.consecutive_failures += 1
            self.db.commit()
            raise

    def _dispatch_scheduled_job(
        self,
        scheduled_job: ScheduledJob,
        *,
        idempotency_key: str,
        user_id: UUID,
        trigger_source: str,
    ) -> Job:
        parameters = scheduled_job.parameters or {}
        operation = parameters.get("operation")
        service = LibroMayorJobService(self.db)

        if scheduled_job.job_type == JobType.LEDGER_SYNC_DELTA.value:
            if operation == "sync_delta_all":
                return service.enqueue_sync_delta_all(
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    batch_size=scheduled_job.batch_size,
                    scheduled_job_id=scheduled_job.id,
                    trigger_source=trigger_source,
                )
            return service.enqueue_sync_delta(
                account=parameters["account"],
                start_date=self._parse_date(parameters.get("start_date")),
                end_date=self._parse_date(parameters.get("end_date")),
                user_id=user_id,
                idempotency_key=idempotency_key,
                batch_size=scheduled_job.batch_size,
                scheduled_job_id=scheduled_job.id,
                trigger_source=trigger_source,
            )

        if scheduled_job.job_type == JobType.LEDGER_SYNC.value:
            return service.enqueue_sync(
                account=parameters["account"],
                start_date=self._parse_required_date(parameters.get("start_date")),
                end_date=self._parse_required_date(parameters.get("end_date")),
                user_id=user_id,
                idempotency_key=idempotency_key,
                batch_size=scheduled_job.batch_size,
                scheduled_job_id=scheduled_job.id,
                trigger_source=trigger_source,
            )

        if scheduled_job.job_type == JobType.LEDGER_REPROCESS.value:
            return service.enqueue_reprocess_date_range(
                account=parameters["account"],
                start_date=self._parse_required_date(parameters.get("start_date")),
                end_date=self._parse_required_date(parameters.get("end_date")),
                user_id=user_id,
                idempotency_key=idempotency_key,
                batch_size=scheduled_job.batch_size,
                scheduled_job_id=scheduled_job.id,
                trigger_source=trigger_source,
            )

        if scheduled_job.job_type == JobType.ANALYTICS_EXTRACT.value:
            ingestion_service = AnalyticsIngestionService(self.db)
            if parameters.get("table_group"):
                table_names = ingestion_service.get_icg_table_names_by_group(
                    parameters["table_group"]
                )
            elif parameters.get("table_names"):
                table_names = parameters["table_names"]
            else:
                table_names = [parameters["table_name"]]

            return ingestion_service.enqueue_icg_tables(
                table_names=table_names,
                mode=parameters.get("mode", "incremental"),
                start_date=self._parse_date(parameters.get("start_date")),
                end_date=self._parse_date(parameters.get("end_date")),
                lookback_days=parameters.get("lookback_days"),
                user_id=user_id,
                idempotency_key=idempotency_key,
                batch_size=scheduled_job.batch_size,
                scheduled_job_id=scheduled_job.id,
                trigger_source=trigger_source,
            )

        raise ValidationError("Tipo de tarea programada no soportado")

    @staticmethod
    def calculate_next_run(
        *,
        schedule_kind: str,
        schedule_config: dict,
        tz_name: str,
        after: datetime | None = None,
    ) -> datetime:
        return calculate_next_run(
            schedule_kind=schedule_kind,
            schedule_config=schedule_config,
            tz_name=tz_name,
            after=after,
        )

    @staticmethod
    def _build_idempotency_key(
        scheduled_job: ScheduledJob,
        due_at: datetime,
        manual: bool,
    ) -> str:
        prefix = "manual" if manual else "scheduled"
        slot = due_at.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{prefix}:{scheduled_job.id}:{slot}"

    @staticmethod
    def _parse_date(value) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @classmethod
    def _parse_required_date(cls, value) -> date:
        parsed = cls._parse_date(value)
        if not parsed:
            raise ValidationError("La fecha es obligatoria para esta tarea")
        return parsed
