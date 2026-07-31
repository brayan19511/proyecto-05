import unittest

from app.api.jobs.constants import JobType
from app.api.sap.handlers import get_sap_item_handler
from app.api.sap.handlers.document_action import SapDocumentActionHandler
from app.api.sap.handlers.reconciliation import SapReconciliationHandler
from app.core.exceptions import ValidationError


class SapHandlerRegistryTests(unittest.TestCase):
    def test_resolves_document_action_handler(self):
        self.assertIs(
            get_sap_item_handler(JobType.SAP_DOCUMENT_ACTION.value),
            SapDocumentActionHandler,
        )

    def test_resolves_reconciliation_handler(self):
        self.assertIs(
            get_sap_item_handler(JobType.SAP_RECONCILIATION.value),
            SapReconciliationHandler,
        )

    def test_rejects_unknown_job_type(self):
        with self.assertRaises(ValidationError):
            get_sap_item_handler("SAP_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
