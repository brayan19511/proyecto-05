import unittest

from app.api.sales_channel.permissions import (
    PROMOTION_EDIT_PERMISSION,
    PROMOTION_IMPORT_PERMISSION,
    PROMOTION_VIEW_PERMISSION,
    SKU_EDIT_PERMISSION,
    SKU_IMPORT_PERMISSION,
    SKU_VIEW_PERMISSION,
)
from app.api.verify.seed_service import PERMISSIONS, ROLE_PERMISSIONS, ROLES


class SeedConfigurationTests(unittest.TestCase):
    def test_permission_codes_are_unique(self):
        codes = [permission["code"] for permission in PERMISSIONS]
        self.assertEqual(len(codes), len(set(codes)))

    def test_role_permissions_reference_declared_permissions(self):
        declared = {permission["code"] for permission in PERMISSIONS}
        assigned = {
            permission
            for permissions in ROLE_PERMISSIONS.values()
            for permission in permissions
        }
        self.assertTrue(assigned.issubset(declared))

    def test_sales_channel_roles_have_expected_permissions(self):
        self.assertIn("Canales Venta Consulta", ROLES)
        self.assertIn("Canales Venta Importador", ROLES)
        self.assertIn("Canales Venta Admin", ROLES)

        self.assertEqual(
            ROLE_PERMISSIONS["Canales Venta Consulta"],
            {SKU_VIEW_PERMISSION, PROMOTION_VIEW_PERMISSION},
        )
        self.assertEqual(
            ROLE_PERMISSIONS["Canales Venta Importador"],
            {
                SKU_VIEW_PERMISSION,
                SKU_IMPORT_PERMISSION,
                PROMOTION_VIEW_PERMISSION,
                PROMOTION_IMPORT_PERMISSION,
            },
        )
        self.assertEqual(
            ROLE_PERMISSIONS["Canales Venta Admin"],
            {
                SKU_VIEW_PERMISSION,
                SKU_EDIT_PERMISSION,
                SKU_IMPORT_PERMISSION,
                PROMOTION_VIEW_PERMISSION,
                PROMOTION_EDIT_PERMISSION,
                PROMOTION_IMPORT_PERMISSION,
            },
        )


if __name__ == "__main__":
    unittest.main()
