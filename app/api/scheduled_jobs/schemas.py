from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.jobs.constants import JobType, ScheduledJobScheduleKind
from app.core.schemas import ORMModel, PageResponse


def _validate_hhmm(value, field_name: str) -> None:
    if not isinstance(value, str) or len(value.split(":")) != 2:
        raise ValueError(f"{field_name} debe tener formato HH:MM")
    hour, minute = value.split(":")
    if not (hour.isdigit() and minute.isdigit()):
        raise ValueError(f"{field_name} debe tener formato HH:MM")
    if int(hour) > 23 or int(minute) > 59:
        raise ValueError(f"{field_name} fuera de rango")


def _minutes_of_day(value: str) -> int:
    hour, minute = [int(part) for part in value.split(":")]
    return hour * 60 + minute


def validate_schedule_config(schedule_kind, value: dict[str, Any]) -> None:
    """Valida schedule_config segun el tipo de agenda. Lanza ValueError.

    Reutilizable tanto por el schema (create) como por el service (update),
    para que un PATCH no pueda dejar una configuracion invalida guardada.
    """
    if schedule_kind == ScheduledJobScheduleKind.DAILY:
        times = value.get("times")
        if not isinstance(times, list) or not times:
            raise ValueError("DAILY requiere schedule_config.times")
        for item in times:
            if not isinstance(item, str) or len(item.split(":")) != 2:
                raise ValueError("Cada hora debe tener formato HH:MM")
            hour, minute = item.split(":")
            if not (hour.isdigit() and minute.isdigit()):
                raise ValueError("Cada hora debe tener formato HH:MM")
            if int(hour) > 23 or int(minute) > 59:
                raise ValueError("Hora fuera de rango")
    if schedule_kind == ScheduledJobScheduleKind.INTERVAL_MINUTES:
        minutes = value.get("minutes")
        if not isinstance(minutes, int) or minutes < 1:
            raise ValueError("INTERVAL_MINUTES requiere minutes mayor que cero")
    if schedule_kind == ScheduledJobScheduleKind.WINDOW_INTERVAL:
        minutes = value.get("minutes")
        weekdays = value.get("weekdays", [0, 1, 2, 3, 4])
        start_time = value.get("start_time")
        end_time = value.get("end_time")
        if not isinstance(minutes, int) or minutes < 1:
            raise ValueError("WINDOW_INTERVAL requiere minutes mayor que cero")
        if not isinstance(weekdays, list) or not weekdays:
            raise ValueError("WINDOW_INTERVAL requiere weekdays")
        if any(not isinstance(day, int) or day < 0 or day > 6 for day in weekdays):
            raise ValueError("weekdays debe usar 0=Lunes hasta 6=Domingo")
        _validate_hhmm(start_time, "start_time")
        _validate_hhmm(end_time, "end_time")
        if _minutes_of_day(start_time) >= _minutes_of_day(end_time):
            raise ValueError("start_time debe ser menor que end_time")


class ScheduledJobBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    job_type: JobType
    enabled: bool = True
    schedule_kind: ScheduledJobScheduleKind
    schedule_config: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    batch_size: int = Field(default=1, ge=1, le=31)
    timezone: str = Field(default="America/Lima", max_length=60)

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, value: JobType):
        supported = {
            JobType.ANALYTICS_EXTRACT,
            JobType.LEDGER_SYNC,
            JobType.LEDGER_SYNC_DELTA,
            JobType.LEDGER_REPROCESS,
        }
        if value not in supported:
            raise ValueError("Solo se soportan tareas programadas de libro mayor o analytics")
        return value

    @field_validator("schedule_config")
    @classmethod
    def _check_schedule_config(cls, value: dict[str, Any], info):
        validate_schedule_config(info.data.get("schedule_kind"), value)
        return value

    @model_validator(mode="after")
    def validate_job_parameters(self):
        if self.job_type == JobType.ANALYTICS_EXTRACT:
            table_name = self.parameters.get("table_name")
            table_names = self.parameters.get("table_names")
            table_group = self.parameters.get("table_group")
            mode = self.parameters.get("mode", "incremental")
            lookback_days = self.parameters.get("lookback_days")
            selectors = [
                isinstance(table_name, str) and bool(table_name.strip()),
                isinstance(table_names, list) and bool(table_names),
                isinstance(table_group, str) and bool(table_group.strip()),
            ]
            if sum(selectors) != 1:
                raise ValueError(
                    "ANALYTICS_EXTRACT requiere solo uno: parameters.table_name, "
                    "parameters.table_names o parameters.table_group"
                )
            if table_names and any(not isinstance(item, str) or not item.strip() for item in table_names):
                raise ValueError("ANALYTICS_EXTRACT parameters.table_names debe contener nombres validos")
            if table_group and table_group not in {"transactional", "master", "all"}:
                raise ValueError("ANALYTICS_EXTRACT parameters.table_group debe ser transactional, master o all")
            if mode not in {"incremental", "reprocess", "snapshot"}:
                raise ValueError(
                    "ANALYTICS_EXTRACT parameters.mode debe ser incremental, reprocess o snapshot"
                )
            if lookback_days is not None and (
                not isinstance(lookback_days, int)
                or lookback_days < 0
                or lookback_days > 31
            ):
                raise ValueError(
                    "ANALYTICS_EXTRACT parameters.lookback_days debe estar entre 0 y 31"
                )
        return self


class ScheduledJobCreate(ScheduledJobBase):
    next_run_at: datetime | None = None


class ScheduledJobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    enabled: bool | None = None
    schedule_kind: ScheduledJobScheduleKind | None = None
    schedule_config: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    batch_size: int | None = Field(default=None, ge=1, le=31)
    timezone: str | None = Field(default=None, max_length=60)
    next_run_at: datetime | None = None


class ScheduledJobResponse(ORMModel):
    id: UUID
    name: str
    job_type: JobType
    enabled: bool
    schedule_kind: ScheduledJobScheduleKind
    schedule_config: dict[str, Any]
    parameters: dict[str, Any]
    batch_size: int
    timezone: str
    next_run_at: datetime
    last_run_at: datetime | None
    last_job_id: UUID | None
    last_status: str | None
    consecutive_failures: int
    last_error: str | None
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime


ScheduledJobPageResponse = PageResponse[ScheduledJobResponse]
