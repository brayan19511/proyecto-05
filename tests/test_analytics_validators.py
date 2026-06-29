from datetime import date
import unittest

from fastapi import HTTPException

from app.api.coolbox.analytics.common.validators import (
    normalize_list,
    normalize_optional,
    validate_date_range,
    validate_limit,
)


class AnalyticsValidatorsTests(unittest.TestCase):
    def test_normalize_optional_removes_blank_values(self):
        self.assertIsNone(normalize_optional("   "))
        self.assertEqual(normalize_optional(" tienda-01 "), "tienda-01")

    def test_normalize_list_cleans_and_deduplicates(self):
        result = normalize_list([" A ", "", "A", "B", "  "])
        self.assertEqual(result, ["A", "B"])

    def test_invalid_date_range_raises_bad_request(self):
        with self.assertRaises(HTTPException) as context:
            validate_date_range(date(2026, 2, 2), date(2026, 2, 1))
        self.assertEqual(context.exception.status_code, 400)

    def test_limit_respects_endpoint_maximum(self):
        validate_limit(100, maximum=100)
        with self.assertRaises(HTTPException):
            validate_limit(101, maximum=100)


if __name__ == "__main__":
    unittest.main()
