import unittest
from datetime import datetime, timezone
from unittest.mock import ANY, Mock, patch
from uuid import uuid4

from app.api.jobs.constants import (
    JobTriggerSource,
    JobType,
    ScheduledJobScheduleKind,
)
from app.api.scheduled_jobs.service import ScheduledJobService
from app.models.jobs import ScheduledJob


class ScheduledJobServiceTests(unittest.TestCase):
    def test_daily_schedule_uses_next_configured_time(self):
        next_run = ScheduledJobService.calculate_next_run(
            schedule_kind=ScheduledJobScheduleKind.DAILY.value,
            schedule_config={"times": ["04:00", "08:00"]},
            tz_name="America/Lima",
            after=datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            next_run,
            datetime(2026, 7, 28, 13, 0, tzinfo=timezone.utc),
        )

    def test_interval_schedule_adds_minutes(self):
        next_run = ScheduledJobService.calculate_next_run(
            schedule_kind=ScheduledJobScheduleKind.INTERVAL_MINUTES.value,
            schedule_config={"minutes": 30},
            tz_name="America/Lima",
            after=datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            next_run,
            datetime(2026, 7, 28, 9, 30, tzinfo=timezone.utc),
        )

    def test_window_interval_respects_business_window(self):
        next_run = ScheduledJobService.calculate_next_run(
            schedule_kind=ScheduledJobScheduleKind.WINDOW_INTERVAL.value,
            schedule_config={
                "weekdays": [0, 1, 2, 3, 4],
                "start_time": "08:00",
                "end_time": "18:00",
                "minutes": 240,
            },
            tz_name="America/Lima",
            after=datetime(2026, 7, 28, 18, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(
            next_run,
            datetime(2026, 7, 28, 21, 0, tzinfo=timezone.utc),
        )

    def test_window_interval_moves_to_next_weekday(self):
        next_run = ScheduledJobService.calculate_next_run(
            schedule_kind=ScheduledJobScheduleKind.WINDOW_INTERVAL.value,
            schedule_config={
                "weekdays": [0, 1, 2, 3, 4],
                "start_time": "08:00",
                "end_time": "18:00",
                "minutes": 240,
            },
            tz_name="America/Lima",
            after=datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            next_run,
            datetime(2026, 8, 3, 13, 0, tzinfo=timezone.utc),
        )

    def test_dispatches_ledger_delta_all_with_scheduled_job_id(self):
        scheduled_job = ScheduledJob(
            id=uuid4(),
            name="Libro mayor delta",
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            schedule_kind=ScheduledJobScheduleKind.DAILY.value,
            schedule_config={"times": ["04:00"]},
            parameters={"operation": "sync_delta_all"},
            batch_size=1,
            timezone="America/Lima",
            next_run_at=datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc),
            created_by=uuid4(),
        )
        service = ScheduledJobService(Mock())

        with patch(
            "app.api.scheduled_jobs.service.LibroMayorJobService"
        ) as job_service_class:
            job_service = job_service_class.return_value
            job_service.enqueue_sync_delta_all.return_value = "job"

            result = service._dispatch_scheduled_job(
                scheduled_job,
                idempotency_key="scheduled-key",
                user_id=scheduled_job.created_by,
                trigger_source=JobTriggerSource.SCHEDULED.value,
            )

        self.assertEqual(result, "job")
        job_service.enqueue_sync_delta_all.assert_called_once_with(
            user_id=scheduled_job.created_by,
            idempotency_key="scheduled-key",
            batch_size=1,
            scheduled_job_id=scheduled_job.id,
            trigger_source=JobTriggerSource.SCHEDULED.value,
        )

    def test_manual_run_uses_current_user_as_job_creator(self):
        scheduled_job = ScheduledJob(
            id=uuid4(),
            name="Libro mayor delta",
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            schedule_kind=ScheduledJobScheduleKind.DAILY.value,
            schedule_config={"times": ["04:00"]},
            parameters={"operation": "sync_delta_all"},
            batch_size=1,
            timezone="America/Lima",
            next_run_at=datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc),
            created_by=uuid4(),
        )
        executor_id = uuid4()
        db = Mock()
        service = ScheduledJobService(db)

        with patch.object(service, "get", return_value=scheduled_job), patch(
            "app.api.scheduled_jobs.service.LibroMayorJobService"
        ) as job_service_class:
            job_service = job_service_class.return_value
            job_service.enqueue_sync_delta_all.return_value = Mock(
                id=uuid4(),
                status="QUEUED",
            )

            service.run_now(scheduled_job.id, user_id=executor_id)

        job_service.enqueue_sync_delta_all.assert_called_once_with(
            user_id=executor_id,
            idempotency_key=ANY,
            batch_size=1,
            scheduled_job_id=scheduled_job.id,
            trigger_source=JobTriggerSource.SCHEDULED_MANUAL.value,
        )


if __name__ == "__main__":
    unittest.main()
