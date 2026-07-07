from datetime import date
from io import BytesIO
import unittest
from unittest.mock import Mock
from uuid import uuid4

from openpyxl import Workbook

from app.api.jobs.constants import JobType
from app.api.jobs.service import JobService
from app.api.sap.service.sap_reconciliation_service import (
    SapReconciliationExcelService,
)
from app.core.exceptions import ValidationError


def build_workbook(rows: list[list]) -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "ReconNum",
            "SrcObjAbs",
            "SrcObjTyp",
            "TransRowId",
            "TransId",
            "Account",
            "ShortName",
            "ReconcileAmount",
        ]
    )
    for row in rows:
        sheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


class SapReconciliationExcelServiceTests(unittest.TestCase):
    def test_builds_one_payload_per_recon_num(self):
        stream = build_workbook(
            [
                ["R1", 7924718, "30", 0, 7924718, None, "C999", 49.9],
                ["R1", 4727493, "30", 298, 4727493, None, "C999", -49.9],
            ]
        )

        payloads = SapReconciliationExcelService().build_payloads(
            stream,
            filename="reconciliacion.xlsx",
            recon_date=date(2026, 7, 6),
        )

        payload = payloads["R1"]
        self.assertEqual(payload["CardOrAccount"], "coaCard")
        self.assertEqual(payload["ReconDate"], "2026-07-06")
        rows = payload["InternalReconciliationOpenTransRows"]
        self.assertEqual(rows[0]["CreditOrDebit"], "codDebit")
        self.assertEqual(rows[1]["CreditOrDebit"], "codCredit")
        self.assertEqual(rows[0]["ReconcileAmount"], 49.9)

    def test_rejects_unbalanced_recon_num(self):
        stream = build_workbook(
            [
                ["R1", 1, "30", 0, 1, None, "C999", 49.9],
                ["R1", 2, "30", 1, 2, None, "C999", -40],
            ]
        )

        with self.assertRaises(ValidationError):
            SapReconciliationExcelService().build_payloads(
                stream,
                filename="reconciliacion.xlsx",
                recon_date=date(2026, 7, 6),
            )


class SapReconciliationJobTests(unittest.TestCase):
    def test_job_items_keep_reconciliation_payloads(self):
        db = Mock()
        service = JobService(db, dispatcher=Mock())
        service.repository = Mock()
        service.repository.get_by_idempotency_key.return_value = None

        created = {}
        service.get_job = Mock(side_effect=lambda job_id, **kwargs: created["job"])
        db.add.side_effect = lambda job: created.update(job=job)

        job = service.create_job(
            job_type=JobType.SAP_RECONCILIATION.value,
            parameters={"database": "COMPANY", "entity": "InternalReconciliations"},
            references=["R1"],
            user_id=uuid4(),
            batch_size=100,
            item_payloads={"R1": {"ReconDate": "2026-07-06"}},
        )

        self.assertEqual(
            job.batches[0].items[0].result_data,
            {"ReconDate": "2026-07-06"},
        )


if __name__ == "__main__":
    unittest.main()
