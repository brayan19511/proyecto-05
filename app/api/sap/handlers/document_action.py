from app.api.sap.handlers.base import SapItemHandler
from app.models.jobs import JobBatch, JobItem


class SapDocumentActionHandler(SapItemHandler):
    """Ejecuta acciones sobre documentos SAP, por ejemplo cancelar/cerrar."""

    def execute(self, batch: JobBatch, item: JobItem):
        parameters = batch.job.parameters
        return self.service.execute(
            self.client,
            entity=parameters["entity"],
            action=parameters["action"],
            document=item.reference,
        )
