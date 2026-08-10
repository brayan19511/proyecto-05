import unittest
from datetime import datetime, timedelta, timezone

from app.api.observability.analytics_service import (
    DEFAULT_WINDOW_HOURS,
    MAX_WINDOW_DAYS,
    resolve_range,
)
from app.api.observability.constants import (
    STATUS_DEGRADED,
    STATUS_DOWN,
    STATUS_OK,
)
from app.api.observability.schemas import ComponentStatus
from app.api.observability.status_service import SystemStatusService
from app.core.exceptions import ValidationError


class ResolveRangeTests(unittest.TestCase):
    def test_defaults_to_last_window(self):
        start, end = resolve_range(None, None)
        self.assertAlmostEqual(
            (end - start).total_seconds(),
            timedelta(hours=DEFAULT_WINDOW_HOURS).total_seconds(),
            delta=5,
        )

    def test_naive_dates_are_treated_as_utc(self):
        start, end = resolve_range(
            datetime(2026, 1, 1, 0, 0),
            datetime(2026, 1, 2, 0, 0),
        )
        self.assertEqual(start.tzinfo, timezone.utc)
        self.assertEqual(end.tzinfo, timezone.utc)

    def test_start_after_end_is_rejected(self):
        with self.assertRaises(ValidationError):
            resolve_range(
                datetime(2026, 1, 2, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_window_over_maximum_is_rejected(self):
        end = datetime(2026, 6, 1, tzinfo=timezone.utc)
        start = end - timedelta(days=MAX_WINDOW_DAYS + 1)
        with self.assertRaises(ValidationError):
            resolve_range(start, end)


class WorstStatusTests(unittest.TestCase):
    def _components(self, *statuses):
        return [
            ComponentStatus(component=f"c{i}", status=status)
            for i, status in enumerate(statuses)
        ]

    def test_all_ok(self):
        result = SystemStatusService._worst_status(
            self._components(STATUS_OK, STATUS_OK)
        )
        self.assertEqual(result, STATUS_OK)

    def test_degraded_beats_ok(self):
        result = SystemStatusService._worst_status(
            self._components(STATUS_OK, STATUS_DEGRADED)
        )
        self.assertEqual(result, STATUS_DEGRADED)

    def test_down_beats_degraded(self):
        result = SystemStatusService._worst_status(
            self._components(STATUS_DEGRADED, STATUS_DOWN, STATUS_OK)
        )
        self.assertEqual(result, STATUS_DOWN)

    def test_empty_is_ok(self):
        self.assertEqual(SystemStatusService._worst_status([]), STATUS_OK)


if __name__ == "__main__":
    unittest.main()
