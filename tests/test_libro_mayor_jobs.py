import unittest
from datetime import date, datetime
from unittest.mock import Mock
from uuid import uuid4

from app.api.finance.libro_mayor.service.libro_mayor_job_service import (
    DEFAULT_LEDGER_START_DATE,
    LibroMayorJobService,
)
from app.api.jobs.constants import JobType


class LibroMayorJobServiceTests(unittest.TestCase):
    def test_build_daily_payloads_splits_range_by_day(self):
        service = LibroMayorJobService.__new__(LibroMayorJobService)

        payloads = service._build_daily_payloads(
            operation="sync_delta",
            accounts=["95"],
            start_date=date(2026, 7, 25),
            end_date=date(2026, 7, 27),
        )

        self.assertEqual(
            list(payloads),
            [
                "sync_delta:95:2026-07-25",
                "sync_delta:95:2026-07-26",
                "sync_delta:95:2026-07-27",
            ],
        )
        self.assertEqual(payloads["sync_delta:95:2026-07-25"]["end_date"], "2026-07-25")

    def test_delta_start_uses_default_when_account_has_no_rows(self):
        service = LibroMayorJobService.__new__(LibroMayorJobService)
        service.repository = Mock()
        service.repository.get_last_libro_mayor.return_value = None

        self.assertEqual(
            service._resolve_delta_start("95", None),
            DEFAULT_LEDGER_START_DATE,
        )

    def test_delta_start_uses_last_local_update_date(self):
        service = LibroMayorJobService.__new__(LibroMayorJobService)
        service.repository = Mock()
        service.repository.get_last_libro_mayor.return_value = Mock(
            fecha_actualizacion=datetime(2026, 7, 25, 4, 0, 1)
        )

        self.assertEqual(
            service._resolve_delta_start("95", None),
            date(2026, 7, 25),
        )

    def test_enqueue_sync_creates_ledger_sync_job_with_daily_payloads(self):
        service = LibroMayorJobService.__new__(LibroMayorJobService)
        service._create_job = Mock(return_value="job")

        result = service.enqueue_sync(
            account="95",
            start_date=date(2026, 7, 25),
            end_date=date(2026, 7, 26),
            user_id=uuid4(),
            idempotency_key="same-request",
            batch_size=1,
        )

        self.assertEqual(result, "job")
        kwargs = service._create_job.call_args.kwargs
        self.assertEqual(kwargs["job_type"], JobType.LEDGER_SYNC.value)
        self.assertEqual(
            list(kwargs["payloads"]),
            ["sync:95:2026-07-25", "sync:95:2026-07-26"],
        )


if __name__ == "__main__":
    unittest.main()
