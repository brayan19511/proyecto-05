import unittest

from app.api.attendance.permissions import ATTENDANCE_MARKS_VIEW_PERMISSION
from app.api.finance.payment_provider.constants import (
    DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER,
)
from app.api.sales_channel.permissions import (
    PROMOTION_EDIT_PERMISSION,
    PROMOTION_IMPORT_PERMISSION,
    PROMOTION_VIEW_PERMISSION,
    SKU_EDIT_PERMISSION,
    SKU_IMPORT_PERMISSION,
    SKU_VIEW_PERMISSION,
)
from app.api.verify.seed_service import (
    DEFAULT_SCHEDULED_JOBS,
    MAILING_PARAMETERS,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    ROLES,
)


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

    def test_attendance_role_has_read_only_permission(self):
        self.assertIn("Asistencia Consulta", ROLES)
        self.assertEqual(
            ROLE_PERMISSIONS["Asistencia Consulta"],
            {ATTENDANCE_MARKS_VIEW_PERMISSION},
        )

    def test_payment_provider_mailing_parameter_is_single_default(self):
        names = [item["name"] for item in MAILING_PARAMETERS]

        self.assertEqual(names, [DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER])
        self.assertEqual(
            MAILING_PARAMETERS[0]["template"],
            "payment_provider_summary.html",
        )

    def test_default_ledger_scheduled_job_is_business_window(self):
        [scheduled_job] = DEFAULT_SCHEDULED_JOBS

        self.assertEqual(scheduled_job["name"], "Libro mayor delta laboral")
        self.assertEqual(scheduled_job["schedule_kind"], "WINDOW_INTERVAL")
        self.assertEqual(
            scheduled_job["schedule_config"],
            {
                "weekdays": [0, 1, 2, 3, 4],
                "start_time": "08:00",
                "end_time": "18:00",
                "minutes": 240,
            },
        )
        self.assertEqual(scheduled_job["parameters"], {"operation": "sync_delta_all"})


if __name__ == "__main__":
    unittest.main()
