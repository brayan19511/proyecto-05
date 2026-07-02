from datetime import date, datetime
import unittest
from unittest.mock import Mock

from sqlalchemy.dialects import mssql
from starlette.datastructures import QueryParams

from app.api.attendance.repository import AttendanceRepository
from app.api.attendance.schemas import AttendanceMarkPage
from app.api.attendance.service import AttendanceService
from app.core.exceptions import ValidationError
from app.core.middleware import sanitize_payload, sanitize_query_params


class AttendanceRepositoryTests(unittest.TestCase):
    def test_query_uses_expanding_bound_document_parameters(self):
        db = Mock()
        count_result = Mock()
        count_result.scalar_one.return_value = 1
        page_result = Mock()
        page_result.mappings.return_value.all.return_value = [
            {
                "sequence_id": 10,
                "document_number": 12345678,
                "marked_at": datetime(2026, 7, 1, 8, 0),
                "mark_date": date(2026, 7, 1),
                "row_number": 1,
                "mark_type": "INGRESO",
            }
        ]
        db.execute.side_effect = [count_result, page_result]

        items, total = AttendanceRepository(db).get_marks(
            [12345678, 87654321],
            date(2026, 7, 1),
            date(2026, 7, 31),
            100,
            0,
        )

        statement, parameters = db.execute.call_args_list[1].args
        sql = str(statement.compile(dialect=mssql.dialect()))
        self.assertIn("POSTCOMPILE_document_numbers", sql)
        self.assertNotIn("12345678", sql)
        self.assertEqual(parameters["document_numbers"], [12345678, 87654321])
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["mark_type"], "INGRESO")


class AttendanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AttendanceService(Mock())
        self.service.repository = Mock()
        self.service.repository.get_marks.return_value = ([], 0)

    def test_deduplicates_documents_before_query(self):
        self.service.repository.get_marks.return_value = (
            [
                {
                    "sequence_id": 1,
                    "document_number": 123,
                    "marked_at": datetime(2026, 7, 1, 8, 0),
                    "mark_date": date(2026, 7, 1),
                    "row_number": 1,
                    "mark_type": "INGRESO",
                }
            ],
            2,
        )

        result = self.service.get_marks(
            [123, 123, 456],
            None,
            None,
            1,
            0,
        )

        arguments = self.service.repository.get_marks.call_args.args
        self.assertEqual(arguments[0], [123, 456])
        self.assertIsInstance(result, AttendanceMarkPage)
        self.assertTrue(result.has_more)

    def test_last_page_does_not_have_more_items(self):
        self.service.repository.get_marks.return_value = ([], 10)

        result = self.service.get_marks(
            [123],
            None,
            None,
            10,
            10,
        )

        self.assertFalse(result.has_more)

    def test_rejects_invalid_date_order(self):
        with self.assertRaisesRegex(
            ValidationError,
            "date_from",
        ):
            self.service.get_marks(
                [123],
                date(2026, 7, 2),
                date(2026, 7, 1),
                100,
                0,
            )

    def test_rejects_more_than_one_year(self):
        with self.assertRaisesRegex(ValidationError, "366"):
            self.service.get_marks(
                [123],
                date(2025, 1, 1),
                date(2026, 7, 1),
                100,
                0,
            )


class AttendanceAuditTests(unittest.TestCase):
    def test_repeated_document_numbers_are_preserved_and_redacted(self):
        sanitized = sanitize_query_params(
            QueryParams(
                "document_number=12345678"
                "&document_number=87654321"
                "&limit=100"
            )
        )

        self.assertEqual(
            sanitized["document_number"],
            ["[REDACTED]", "[REDACTED]"],
        )
        self.assertEqual(sanitized["limit"], "100")

    def test_document_numbers_are_redacted_from_request_body(self):
        sanitized = sanitize_payload(
            {
                "document_numbers": [12345678, 87654321],
                "limit": 100,
            }
        )

        self.assertEqual(sanitized["document_numbers"], "[REDACTED]")
        self.assertEqual(sanitized["limit"], 100)


if __name__ == "__main__":
    unittest.main()
