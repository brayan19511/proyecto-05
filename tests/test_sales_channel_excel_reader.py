from io import BytesIO
import unittest
from unittest.mock import Mock

from fastapi import UploadFile
from openpyxl import Workbook

from app.api.sales_channel.imports.excel_reader import parse_sku_workbook
from app.api.sales_channel.imports.schemas import SkuImportMode
from app.api.sales_channel.imports.service import SkuExcelImportService


def make_upload(headers, rows, filename="skus.xlsx"):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)

    content = BytesIO()
    workbook.save(content)
    workbook.close()
    content.seek(0)
    return UploadFile(file=content, filename=filename)


class SalesChannelExcelReaderTests(unittest.TestCase):
    def test_reads_active_snapshot_with_sku_column(self):
        upload = make_upload(["SKU"], [["SKU-1"], [" SKU-2 "]])

        parsed = parse_sku_workbook(
            upload,
            SkuImportMode.ACTIVE_SNAPSHOT,
        )

        self.assertEqual(parsed.rows, [{"sku": "SKU-1"}, {"sku": "SKU-2"}])
        self.assertEqual(parsed.errors, [])

    def test_reads_status_alias_and_on_off_values(self):
        upload = make_upload(
            ["sku", "on/off"],
            [["SKU-1", "on"], ["SKU-2", "off"]],
        )

        parsed = parse_sku_workbook(
            upload,
            SkuImportMode.STATUS_UPDATE,
        )

        self.assertEqual(
            parsed.rows,
            [
                {"sku": "SKU-1", "active": True},
                {"sku": "SKU-2", "active": False},
            ],
        )

    def test_reports_duplicate_sku_with_row_number(self):
        upload = make_upload(["sku"], [["SKU-1"], [" sku-1 "]])

        parsed = parse_sku_workbook(
            upload,
            SkuImportMode.ACTIVE_SNAPSHOT,
        )

        self.assertEqual(len(parsed.errors), 1)
        self.assertEqual(parsed.errors[0].row, 3)
        self.assertIn("duplicado", parsed.errors[0].message)

    def test_status_update_requires_status_column(self):
        upload = make_upload(["sku"], [["SKU-1"]])

        parsed = parse_sku_workbook(
            upload,
            SkuImportMode.STATUS_UPDATE,
        )

        self.assertFalse(parsed.rows)
        self.assertEqual(parsed.errors[0].field, "active")

    def test_import_rejects_file_different_from_preview_hash(self):
        upload = make_upload(["sku"], [["SKU-1"]])
        service = Mock()

        result = SkuExcelImportService().import_managed(
            upload,
            SkuImportMode.ACTIVE_SNAPSHOT,
            True,
            service,
            expected_sha256="0" * 64,
        )

        self.assertFalse(result.can_apply)
        self.assertFalse(result.applied)
        service.apply_active_snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
