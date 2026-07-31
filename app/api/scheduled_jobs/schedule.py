from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.jobs.constants import ScheduledJobScheduleKind
from app.core.exceptions import ValidationError


def calculate_next_run(
    *,
    schedule_kind: str,
    schedule_config: dict,
    tz_name: str,
    after: datetime | None = None,
) -> datetime:
    tz = validate_timezone(tz_name)
    current = (after or datetime.now(timezone.utc)).astimezone(tz)

    if schedule_kind == ScheduledJobScheduleKind.INTERVAL_MINUTES.value:
        minutes = int(schedule_config["minutes"])
        return (current + timedelta(minutes=minutes)).astimezone(timezone.utc)

    if schedule_kind == ScheduledJobScheduleKind.WINDOW_INTERVAL.value:
        return _next_window_interval(
            current=current,
            schedule_config=schedule_config,
        ).astimezone(timezone.utc)

    if schedule_kind == ScheduledJobScheduleKind.DAILY.value:
        candidates = []
        for value in schedule_config["times"]:
            hour, minute = [int(part) for part in value.split(":")]
            candidate = datetime.combine(
                current.date(),
                time(hour=hour, minute=minute),
                tzinfo=tz,
            )
            if candidate <= current:
                candidate += timedelta(days=1)
            candidates.append(candidate)
        return min(candidates).astimezone(timezone.utc)

    raise ValidationError("Tipo de calendario no soportado")


def validate_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as error:
        raise ValidationError("Zona horaria no soportada") from error


def _next_window_interval(
    *,
    current: datetime,
    schedule_config: dict,
) -> datetime:
    minutes = int(schedule_config["minutes"])
    weekdays = set(schedule_config.get("weekdays", [0, 1, 2, 3, 4]))
    start_at = _parse_time(schedule_config["start_time"])
    end_at = _parse_time(schedule_config["end_time"])

    for day_offset in range(0, 8):
        candidate_date = current.date() + timedelta(days=day_offset)
        if candidate_date.weekday() not in weekdays:
            continue

        window_start = datetime.combine(
            candidate_date,
            start_at,
            tzinfo=current.tzinfo,
        )
        window_end = datetime.combine(
            candidate_date,
            end_at,
            tzinfo=current.tzinfo,
        )
        candidate = window_start
        while candidate <= window_end:
            if candidate > current:
                return candidate
            candidate += timedelta(minutes=minutes)

    raise ValidationError("No se pudo calcular la siguiente ejecucion")


def _parse_time(value: str) -> time:
    hour, minute = [int(part) for part in value.split(":")]
    return time(hour=hour, minute=minute)
