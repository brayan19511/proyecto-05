import unittest

from app.api.sales_channel.channel_registry import (
    CountryCode,
    ProviderCode,
    get_sales_channel,
)
from app.main import app


class SalesChannelRoutesTests(unittest.TestCase):
    def test_rappi_mexico_routes_are_published(self):
        paths = app.openapi()["paths"]
        expected_paths = {
            "/api/sales-channels/mx/rappi/skus",
            "/api/sales-channels/mx/rappi/skus/bulk-sync",
            "/api/sales-channels/mx/rappi/skus/active-snapshot",
            "/api/sales-channels/mx/rappi/skus/{sku}",
            "/api/sales-channels/mx/rappi/skus/{sku}/activate",
            "/api/sales-channels/mx/rappi/skus/{sku}/deactivate",
        }

        self.assertTrue(expected_paths.issubset(paths))

    def test_routes_use_country_before_provider(self):
        paths = app.openapi()["paths"]

        self.assertIn("/api/sales-channels/pe/rappi/skus", paths)
        self.assertIn("/api/sales-channels/pe/peya/skus", paths)
        self.assertIn(
            "/api/sales-channels/pe/rappi/skus/import/preview",
            paths,
        )
        self.assertIn(
            "/api/sales-channels/pe/peya/promo-skus/import",
            paths,
        )
        self.assertNotIn("/api/sales-channels/rappi/skus", paths)
        self.assertNotIn("/api/sales-channels/rappi-mx/skus", paths)

    def test_registry_rejects_unsupported_country_provider_pair(self):
        with self.assertRaisesRegex(ValueError, "Canal no configurado"):
            get_sales_channel(CountryCode.MEXICO, ProviderCode.PEYA)

    def test_openapi_operation_ids_are_unique(self):
        operation_ids = [
            operation["operationId"]
            for path_item in app.openapi()["paths"].values()
            for operation in path_item.values()
            if isinstance(operation, dict) and "operationId" in operation
        ]

        self.assertEqual(len(operation_ids), len(set(operation_ids)))


if __name__ == "__main__":
    unittest.main()
