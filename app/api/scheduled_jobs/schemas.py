from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.api.jobs.constants import JobType, ScheduledJobScheduleKind
from app.core.schemas import ORMModel, PageResponse


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
            JobType.LEDGER_SYNC,
            JobType.LEDGER_SYNC_DELTA,
            JobType.LEDGER_REPROCESS,
        }
        if value not in supported:
            raise ValueError("Solo se soportan tareas programadas de libro mayor")
        return value

    @field_validator("schedule_config")
    @classmethod
    def validate_schedule_config(cls, value: dict[str, Any], info):
        schedule_kind = info.data.get("schedule_kind")
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
            cls._validate_hhmm(start_time, "start_time")
            cls._validate_hhmm(end_time, "end_time")
            if cls._minutes_of_day(start_time) >= cls._minutes_of_day(end_time):
                raise ValueError("start_time debe ser menor que end_time")
        return value

    @staticmethod
    def _validate_hhmm(value, field_name: str) -> None:
        if not isinstance(value, str) or len(value.split(":")) != 2:
            raise ValueError(f"{field_name} debe tener formato HH:MM")
        hour, minute = value.split(":")
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError(f"{field_name} debe tener formato HH:MM")
        if int(hour) > 23 or int(minute) > 59:
            raise ValueError(f"{field_name} fuera de rango")

    @staticmethod
    def _minutes_of_day(value: str) -> int:
        hour, minute = [int(part) for part in value.split(":")]
        return hour * 60 + minute


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
