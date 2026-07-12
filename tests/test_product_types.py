import unittest

from app.api.coolbox.common.product_types import (
    ANALYTICS_PRODUCT_TYPE,
    analytics_product_type_filter,
    analytics_product_type_params,
    normalize_product_type,
)


class ProductTypesTests(unittest.TestCase):
    def test_normalize_product_type_is_index_friendly(self):
        self.assertEqual(normalize_product_type(" pro "), "PRO")
        self.assertEqual(normalize_product_type(""), "OTROS")
        self.assertEqual(normalize_product_type(None), "OTROS")

    def test_analytics_product_filter_uses_bound_param(self):
        self.assertEqual(ANALYTICS_PRODUCT_TYPE, "PRO")
        self.assertEqual(analytics_product_type_filter(), "AND p.tipo = :analytics_product_type")
        self.assertEqual(
            analytics_product_type_params(),
            {"analytics_product_type": "PRO"},
        )


if __name__ == "__main__":
    unittest.main()
