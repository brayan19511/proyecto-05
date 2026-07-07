from app.api.sap.handlers.base import SapItemHandler
from app.models.jobs import JobBatch, JobItem


class SapReconciliationHandler(SapItemHandler):
    """Ejecuta una conciliacion interna SAP generada desde el Excel."""

    def execute(self, batch: JobBatch, item: JobItem):
        # item.reference es el ReconNum. El payload completo se guardo en
        # result_data al crear la tarea, asi el worker no depende del archivo.
        return self.service.execute_reconciliation(
            self.client,
            payload=item.result_data or {},
        )
